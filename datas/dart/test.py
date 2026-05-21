import os
from dotenv import load_dotenv

load_dotenv()

from pykrx import stock
import pandas as pd
import numpy as np

def test_actual_insert_value():
    ticker = "464170" # 신한제18호스팩
    print(f"=== [{ticker}] DB 적재 직전 데이터 값 추적 ===")

    try:
        # 이 종목이 거래되었던 최근 3년 치를 모두 조회해서 살아있던 날짜를 찾습니다.
        df_ohlcv = stock.get_market_ohlcv_by_date("20230101", "20260515", ticker)
        
        if df_ohlcv is None or df_ohlcv.empty:
            print("최근 3년 동안 거래된 주가 데이터가 아예 없습니다.")
            return
            
        # 데이터가 존재하는 첫 번째 날짜를 타겟팅합니다.
        real_target_date = df_ohlcv.index[0].strftime("%Y%m%d")
        print(f"✅ 살아있던 거래일 발견: {real_target_date}")
        
        df_cap = stock.get_market_cap_by_date(real_target_date, real_target_date, ticker)
        
        # 1. 뼈대 결합 (이날 하루 치)
        df_target_ohlcv = df_ohlcv.loc[[df_ohlcv.index[0]]]
        df_total = df_target_ohlcv[['종가', '거래량']].join(df_cap['시가총액'], how='left')

        # 2. 퀀트 지표
        try:
            df_fund = stock.get_market_fundamental_by_date(real_target_date, real_target_date, ticker)
            if df_fund is not None and not df_fund.empty:
                fund_cols = [c for c in ['PER', 'PBR', 'DIV'] if c in df_fund.columns]
                df_total = df_total.join(df_fund[fund_cols], how='left')
        except Exception:
            pass

        # 3. 공매도 지표
        try:
            df_short = stock.get_shorting_volume_by_date(real_target_date, real_target_date, ticker)
            if df_short is not None and not df_short.empty and '비중' in df_short.columns:
                df_total = df_total.join(df_short[['비중']], how='left')
        except Exception:
            pass

        # 4. 결측치 처리
        df_total = df_total.replace([np.nan, np.inf, -np.inf], None)

        # 5. 파이썬 내부 상태 출력
        for date, row in df_total.iterrows():
            r = row.to_dict()
            
            print("\n🚀 [파이썬 엔진 내부 상태] 이 데이터 포맷 그대로 SQL에 전달됩니다:")
            print("-" * 60)
            print(f" 날짜 (base_date)      : {date.strftime('%Y-%m-%d')}")
            print(f" 종가 (close_price)    : {r.get('종가')}")
            print(f" 거래량 (volume)       : {r.get('거래량')}")
            print(f" 시가총액 (market_cap) : {r.get('시가총액')}")
            print(f" PER                   : {r.get('PER')}  <- (이게 None이면 DB에 NULL로 안착)")
            print(f" PBR                   : {r.get('PBR')}  <- (이게 None이면 DB에 NULL로 안착)")
            print(f" 배당수익률 (DIV)      : {r.get('DIV')}  <- (이게 None이면 DB에 NULL로 안착)")
            print(f" 공매도비중 (비중)     : {r.get('비중')}  <- (이게 None이면 DB에 NULL로 안착)")
            print("-" * 60)
            break 

    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    test_actual_insert_value()