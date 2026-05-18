import os
import time
from dotenv import load_dotenv

load_dotenv()

import psycopg2
from datetime import datetime, timedelta
from pykrx import stock
import pandas as pd
import numpy as np

DATABASE_URL = os.getenv("DATABASE_URL")

def collect_stock_prices():
    print("2탄 고도화: 시장 지표 및 퀀트/공매도 시계열 수집 시작...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute("SELECT stock_code, corp_name FROM company WHERE stock_code IS NOT NULL;")
        companies = cursor.fetchall()
        
        if not companies:
            print("대상 상장사가 없습니다. 0탄 수집을 먼저 확인하세요.")
            return
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return

    end_date = datetime.today()
    begin_date = end_date - timedelta(days=3 * 365)
    start_str, end_str = begin_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")

    insert_query = """
        INSERT INTO stock_price (
            stock_code, base_date, close_price, market_cap, volume, 
            per, pbr, dividend_yield, foreign_net_buy, institutional_net_buy, short_ratio
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (stock_code, base_date) 
        DO UPDATE SET 
            close_price = EXCLUDED.close_price,
            market_cap = EXCLUDED.market_cap,
            volume = EXCLUDED.volume,
            per = EXCLUDED.per,
            pbr = EXCLUDED.pbr,
            dividend_yield = EXCLUDED.dividend_yield,
            foreign_net_buy = EXCLUDED.foreign_net_buy,
            institutional_net_buy = EXCLUDED.institutional_net_buy,
            short_ratio = EXCLUDED.short_ratio;
    """

    for idx, (stock_code, corp_name) in enumerate(companies, 1):
        print(f"\n[{idx}/{len(companies)}] {corp_name} ({stock_code}) 데이터 수집 중...")
        try:
            time.sleep(1) # KRX 서버 IP 차단 및 DDoS 오탐지 방지 안정화 시간
            
            # 1. 필수 주가 및 시가총액 (OHLCV & Market Cap)
            df_ohlcv = stock.get_market_ohlcv_by_date(start_str, end_str, stock_code)
            df_cap = stock.get_market_cap_by_date(start_str, end_str, stock_code)
            
            if df_ohlcv is None or df_ohlcv.empty or '종가' not in df_ohlcv.columns:
                print(f"  -> 주가 데이터 없음 (스팩 또는 거래정지 종목 패스)")
                continue
                
            df_total = df_ohlcv[['종가', '거래량']].join(df_cap['시가총액'], how='left')

            # 2. 펀더멘탈 지표 (PER, PBR, DIV) - 시계열 전용 함수로 원상복구 완료
            try:
                df_fund = stock.get_market_fundamental_by_date(start_str, end_str, stock_code)
                if df_fund is not None and not df_fund.empty:
                    fund_cols = [c for c in ['PER', 'PBR', 'DIV'] if c in df_fund.columns]
                    if fund_cols:
                        df_total = df_total.join(df_fund[fund_cols], how='left')
                        print(f"  -> 퀀트 지표(PER/PBR/배당) 결합 성공")
                else:
                    print(f"  -> 펀더멘탈 데이터셋이 비어있음")
            except Exception as e:
                print(f"  -> 펀더멘탈 수집 실패: {e}")

            # 3. 매매동향 (외국인순매수, 기관순매수)
            try:
                df_trading = stock.get_market_trading_value_by_date(start_str, end_str, stock_code)
                if df_trading is not None and not df_trading.empty:
                    trade_cols = [c for c in ['외국인합계', '기관합계'] if c in df_trading.columns]
                    if trade_cols:
                        df_total = df_total.join(df_trading[trade_cols], how='left')
                        print(f"  -> 수급 지표(외국인/기관) 결합 성공")
            except Exception as e:
                print(f"  -> 매매동향 수집 실패: {e}")

            # 4. 공매도 비중 수집 고도화 (short_ratio)
            try:
                df_short = stock.get_shorting_volume_by_date(start_str, end_str, stock_code)
                if df_short is not None and not df_short.empty:
                    short_col = None
                    for c in ['비중', '공매도비중']: # pykrx 버전에 따른 컬럼명 유연화 처리
                        if c in df_short.columns:
                            short_col = c
                            break
                    if short_col:
                        df_total = df_total.join(df_short[[short_col]].rename(columns={short_col: '비중'}), how='left')
                        print(f"  -> 공매도 지표 결합 성공")
                    else:
                        print(f"  -> 공매도 테이블 내 '비중' 컬럼 없음. 컬럼목록: {df_short.columns.tolist()}")
                else:
                    print(f"  -> 공매도 데이터셋이 비어있음")
            except Exception as e:
                print(f"  -> 공매도 수집 실패: {e}")

            # NaN/INF 값을 PostgreSQL에 안전하게 매핑하기 위해 파이썬 None으로 치환
            df_total = df_total.replace([np.nan, np.inf, -np.inf], None)

            # DB 데이터 적재 실행
            inserted_count = 0
            for date, row in df_total.iterrows():
                r = row.to_dict()
                try:
                    cursor.execute(insert_query, (
                        stock_code,
                        date.strftime('%Y-%m-%d'),
                        int(r.get('종가', 0)) if pd.notna(r.get('종가')) else 0,
                        int(r.get('시가총액', 0)) if pd.notna(r.get('시가총액')) else 0,
                        int(r.get('거래량', 0)) if pd.notna(r.get('거래량')) else 0,
                        float(r.get('PER')) if pd.notna(r.get('PER')) and r.get('PER') else None,
                        float(r.get('PBR')) if pd.notna(r.get('PBR')) and r.get('PBR') else None,
                        float(r.get('DIV')) if pd.notna(r.get('DIV')) and r.get('DIV') else None,
                        int(r.get('외국인합계')) if pd.notna(r.get('외국인합계')) and r.get('외국인합계') else None,
                        int(r.get('기관합계')) if pd.notna(r.get('기관합계')) and r.get('기관합계') else None,
                        float(r.get('비중')) if pd.notna(r.get('비중')) and r.get('비중') else None
                    ))
                    inserted_count += 1
                except Exception:
                    continue
                
            conn.commit()
            print(f"  -> Supabase 테이블 적재 최종 완료 ({inserted_count}건)")
            
        except Exception as e:
            conn.rollback()
            print(f"  -> [{corp_name}] 치명적 에러 패스: {e}")

    cursor.close()
    conn.close()
    print("\n모든 기업의 시계열 투자 지표 수집 프로세스가 완료되었습니다.")

if __name__ == "__main__":
    collect_stock_prices()