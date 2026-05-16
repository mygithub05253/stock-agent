import os
import time
import requests
import psycopg2
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
DART_API_KEY = os.getenv("DART_API_KEY")

def collect_financial_statements():
    print("🚀 3탄: 핵심 재무제표 수치 데이터 수집 시작...")
    
    if not DART_API_KEY:
        print("❌ 에러: .env 파일에 DART_API_KEY가 설정되지 않았습니다.")
        return

    # 1. DB에서 재무제표를 수집할 대상 기업(corp_code) 조회
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute("SELECT corp_code, corp_name FROM company;")
        companies = cursor.fetchall()
        
        if not companies:
            print("⚠️ DB에 등록된 기업이 없습니다. DART 수집을 먼저 완료해주세요.")
            return
            
        print(f"🔎 재무제표 수집 대상 기업: {len(companies)}곳")
        
    except Exception as e:
        print(f"❌ DB 조회 실패: {e}")
        return

    # 2. 수집할 연도 및 리포트 코드 설정 (11011 = 사업보고서/연간)
    # 현재가 2026년이므로, 확정된 2024년과 2025년 연간 보고서를 타겟팅합니다.
    target_years = [2024, 2025]
    report_code = "11011" 
    
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
    insert_query = """
        INSERT INTO financial_statement (corp_code, bsns_year, reprt_code, fs_div, account_nm, amount)
        VALUES (%s, %s, %s, %s, %s, %s);
    """

    total_inserted = 0

    try:
        for corp_code, corp_name in companies:
            for year in target_years:
                print(f"📊 [{corp_name}] {year}년 사업보고서 재무 데이터 요청 중...")
                
                params = {
                    "crtfc_key": DART_API_KEY,
                    "corp_code": corp_code,
                    "bsns_year": str(year),
                    "reprt_code": report_code
                }
                
                # OpenDART API 트래픽 제한 우회 (0.5초 대기)
                time.sleep(0.5)
                
                try:
                    response = requests.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                except Exception as e:
                    print(f"⚠️ [{corp_name}] API 요청 실패: {e}")
                    continue

                # 데이터가 없는 경우 (status가 "000"이 아니면 데이터 없음)
                if data.get("status") != "000":
                    print(f"ℹ️ [{corp_name}] {year}년 데이터 없음: {data.get('message')}")
                    continue

                account_list = data.get("list", [])
                
                # 중복 적재 방지: 해당 기업의 해당 연도 기존 데이터가 있다면 먼저 삭제(Clean Insert)
                cursor.execute("""
                    DELETE FROM financial_statement 
                    WHERE corp_code = %s AND bsns_year = %s AND reprt_code = %s;
                """, (corp_code, year, report_code))

                for acnt in account_list:
                    # 주요 계정 과목 필터링 (자산, 부채, 자본, 매출, 영업이익, 당기순이익)
                    account_nm = acnt.get("account_nm", "").strip()
                    fs_div = acnt.get("fs_div", "OFS") # CFS: 연결, OFS: 별도
                    
                    # 수치 데이터 정제 (문자열 -> 숫자, 공백이나 '-' 처리)
                    raw_amount = acnt.get("thstrm_amount", "").replace(",", "").strip()
                    if not raw_amount or raw_amount == "-":
                        amount = 0
                    else:
                        try:
                            amount = int(raw_amount)
                        except ValueError:
                            amount = 0

                    # DB 적재
                    cursor.execute(insert_query, (corp_code, year, report_code, fs_div, account_nm, amount))
                    total_inserted += 1
                
                # 연도별로 즉시 커밋
                conn.commit()
                
        print(f"✅ 성공: 총 {total_inserted}건의 재무제표 계정 데이터가 financial_statement 테이블에 저장되었습니다.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 재무 데이터 처리 중 전체 에러 발생: {e}")
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    collect_financial_statements()