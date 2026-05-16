import os
from dotenv import load_dotenv

load_dotenv()

import psycopg2
from datetime import datetime, timedelta
from pykrx import stock  # 이제 정상적으로 ID/PW를 채워서 출발합니다.
import pandas as pd


DATABASE_URL = os.getenv("DATABASE_URL")

def collect_stock_prices():
    print("🚀 2탄: 일별 주가 및 시가총액 시계열 데이터 수집 시작...")

    # 1. DB에서 주가를 수집할 상장사 stock_code 목록 조회
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute("SELECT stock_code, corp_name FROM company WHERE stock_code IS NOT NULL;")
        companies = cursor.fetchall()
        
        if not companies:
            print("⚠️ DB에 등록된 상장사가 없습니다. DART 수집(100건)을 먼저 완료해주세요.")
            return
            
        print(f"🔎 주가 수집 대상 기업: {len(companies)}곳")
        
    except Exception as e:
        print(f"❌ DB 조회 실패: {e}")
        return

    # 2. 수집 기간 설정 (DART 공시 수집 기간과 맞추기 위해 최근 90일로 설정)
    end_date = datetime.today()
    begin_date = end_date - timedelta(days=90)
    
    start_str = begin_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    
    print(f"📡 시계열 수집 기간: {begin_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")

    # 3. 주가 적재를 위한 쿼리 (중복 날짜 데이터는 최신으로 업데이트)
    insert_query = """
        INSERT INTO stock_price (stock_code, base_date, close_price, market_cap, volume)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (stock_code, base_date) 
        DO UPDATE SET 
            close_price = EXCLUDED.close_price,
            market_cap = EXCLUDED.market_cap,
            volume = EXCLUDED.volume;
    """

    total_inserted = 0

    try:
        for stock_code, corp_name in companies:
            print(f"📈 [{corp_name} ({stock_code})] 데이터 다운로드 중...")
            
            # pykrx를 이용해 해당 기간의 일별 가격 정보(OHLCV) 및 시가총액 조회
            df_ohlcv = stock.get_market_ohlcv_by_date(start_str, end_str, stock_code)
            df_cap = stock.get_market_cap_by_date(start_str, end_str, stock_code)
            
            if df_ohlcv.empty or df_cap.empty:
                print(f"⚠️ [{corp_name}] 해당 기간의 거래 데이터가 존재하지 않습니다. (비상장사 등)")
                continue
            
            # 날짜(Index)를 기준으로 종가, 거래량, 시가총액 데이터 병합
            df_total = pd.merge(df_ohlcv[['종가', '거래량']], df_cap['시가총액'], left_index=True, right_index=True)
            
            # 행별로 루프를 돌며 DB에 삽입
            for date, row in df_total.iterrows():
                base_date = date.strftime('%Y-%m-%d')
                close_price = int(row['종가'])
                volume = int(row['거래량'])
                market_cap = int(row['시가총액'])
                
                cursor.execute(insert_query, (stock_code, base_date, close_price, market_cap, volume))
                total_inserted += 1
                
        conn.commit()
        print(f"✅ 성공: 총 {total_inserted}건의 일별 시세 데이터가 stock_price 테이블에 누적되었습니다.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 주가 데이터 처리 중 에러 발생: {e}")
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    collect_stock_prices()