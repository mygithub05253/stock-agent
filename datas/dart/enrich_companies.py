import os
import io
import requests
import psycopg2
import pandas as pd
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def enrich_company_master():
    print("기업 마스터 정보(업종, 상장일) 보완 시작...")
    
    # 1. Supabase에서 stock_code가 있지만 sector 정보가 없는 기업 목록 조회
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT stock_code FROM company 
            WHERE stock_code IS NOT NULL AND sector IS NULL;
        """)
        target_companies = [row[0] for row in cursor.fetchall()]
        
        if not target_companies:
            print("이미 모든 상장사의 업종 정보가 채워져 있습니다!")
            return
            
        print(f"정보 업데이트가 필요한 상장사: {len(target_companies)}곳")
        
    except Exception as e:
        print(f"DB 조회 실패: {e}")
        return

    # 2. KRX KIND 공식 상장법인 채널에서 직접 데이터 다운로드 (FDR 컬럼 유실 우회)
    print("KRX KIND 공식 상장법인 상세 정보 로드 중...")
    try:
        url = 'http://kind.krx.co.kr/corpgeneral/corpList.do'
        params = {
            'method': 'download',
            'searchType': '13',  # 상장법인 검색 유형 고정
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        # HTML 테이블 읽기 (KIND 엑셀 다운로드는 실제 내부는 HTML 구조입니다)
        dfs = pd.read_html(io.BytesIO(response.content))
        if not dfs:
            print("KRX 데이터를 테이블로 변환할 수 없습니다.")
            return
            
        df_krx = dfs[0]
        
        # 종목코드 문자열 포맷팅 (정수가 소수점 처리되는 버그 방지 및 6자리 zfill)
        df_krx['종목코드'] = df_krx['종목코드'].astype(str).str.split('.').str[0].str.zfill(6)
        df_krx.set_index('종목코드', inplace=True)
        
    except Exception as e:
        print(f"KRX 공식 데이터 로드 또는 파싱 실패: {e}")
        print("팁: lxml 모듈이 없을 경우 발생할 수 있으니 에러 지속 시 'pip install lxml'을 실행하세요.")
        return

    # 3. DB 데이터 업데이트 진행 (KIND 데이터셋은 한글 컬럼명 '업종', '상장일'을 사용합니다)
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
                
                # 중복 데이터 존재 시 첫 행 선택
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[0]
                
                sector = row['업종'] if pd.notnull(row['업종']) else None
                raw_date = row['상장일']
                
                # 날짜 포맷팅 정제 (타임스탬프 또는 문자열 대응)
                listing_date = None
                if pd.notnull(raw_date):
                    if isinstance(raw_date, str):
                        listing_date = raw_date.split()[0]
                    else:
                        listing_date = pd.to_datetime(raw_date).strftime('%Y-%m-%d')

                # DB 업데이트 실행
                cursor.execute(update_query, (sector, listing_date, stock_code))
                updated_count += 1
        
        conn.commit()
        print(f"총 {updated_count}개 기업의 업종 및 상장일 정보가 Supabase에 동기화되었습니다.")
        
    except Exception as e:
        conn.rollback()
        print(f"DB 업데이트 중 오류 발생: {e}")
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    enrich_company_master()