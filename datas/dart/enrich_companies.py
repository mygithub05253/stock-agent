import os
import io
import requests
import psycopg2
import pandas as pd
from dotenv import load_dotenv

# 기업 마스터 정보 보완
# 상장일 정보 전체를 동기화하므로 기간 제한 없이 기존 데이터를 확실하게 보완합니다.

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def enrich_company_master():
    print("기업 마스터 정보(업종, 상장일) 보완 시작...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT stock_code FROM company 
            WHERE stock_code IS NOT NULL AND sector IS NULL;
        """)
        target_companies = [row[0] for row in cursor.fetchall()]
        
        if not target_companies:
            print("이미 모든 상장사의 업종 정보가 채워져 있습니다.")
            return
            
        print(f"정보 업데이트가 필요한 상장사: {len(target_companies)}곳")
        
    except Exception as e:
        print(f"DB 조회 실패: {e}")
        return

    print("KRX KIND 공식 상장법인 상세 정보 로드 중...")
    try:
        url = 'http://kind.krx.co.kr/corpgeneral/corpList.do'
        params = {'method': 'download', 'searchType': '13'}
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        dfs = pd.read_html(io.BytesIO(response.content))
        if not dfs:
            print("KRX 데이터를 테이블로 변환할 수 없습니다.")
            return
            
        df_krx = dfs[0]
        df_krx['종목코드'] = df_krx['종목코드'].astype(str).str.split('.').str[0].str.zfill(6)
        df_krx.set_index('종목코드', inplace=True)
        
    except Exception as e:
        print(f"KRX 공식 데이터 로드 또는 파싱 실패: {e}")
        return

    update_query = """
        UPDATE company 
        SET sector = %s, listing_date = %s 
        WHERE stock_code = %s;
    """
    
    updated_count = 0
    try:
        for stock_code in target_companies:
            if stock_code in df_krx.index:
                row = df_krx.loc[stock_code]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[0]
                
                sector = row['업종'] if pd.notnull(row['업종']) else None
                raw_date = row['상장일']
                
                listing_date = None
                if pd.notnull(raw_date):
                    if isinstance(raw_date, str):
                        listing_date = raw_date.split()[0]
                    else:
                        listing_date = pd.to_datetime(raw_date).strftime('%Y-%m-%d')

                cursor.execute(update_query, (sector, listing_date, stock_code))
                updated_count += 1
        
        conn.commit()
        print(f"성공: 총 {updated_count}개 기업의 업종 및 상장일 정보가 동기화되었습니다.")
        
    except Exception as e:
        conn.rollback()
        print(f"DB 업데이트 중 오류 발생: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    enrich_company_master()