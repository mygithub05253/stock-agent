import os
import time
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
DART_API_KEY = os.getenv("DART_API_KEY")

def collect_financial_statements():
    print("전체 재무제표 수집 파이프라인 시작 (팬젠부터 완벽하게 이어하기)...\n")
    
    if not DART_API_KEY:
        print("DART_API_KEY 누락")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # 💡 [핵심 복구 1] 정렬(ORDER BY)을 완전히 빼서 선생님이 처음 돌리셨던 그 401개 순서 그대로 복구합니다.
        cursor.execute("SELECT corp_code, corp_name FROM company;")
        companies = cursor.fetchall()
        
        if not companies:
            print("DB에 저장된 기업(company) 데이터가 없습니다. 1탄 스크립트를 먼저 실행해주세요.")
            return
    except Exception as e:
        print(f"DB 연결 및 조회 실패: {e}")
        return

    explicit_targets = [
        (2025, "11013"), # 25년 1분기
        (2025, "11012"), # 25년 반기
        (2025, "11014"), # 25년 3분기
        (2025, "11011"), # 25년 사업보고서
        (2026, "11013")  # 26년 1분기
    ]
    
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"

    fs_insert = """
        INSERT INTO financial_statement (corp_code, bsns_year, reprt_code, fs_div, account_nm, amount)
        VALUES (%s, %s, %s, %s, %s, %s);
    """
    ratio_upsert = """
        INSERT INTO financial_ratio (corp_code, bsns_year, reprt_code, fs_div, debt_ratio, roe)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (corp_code, bsns_year, reprt_code, fs_div)
        DO UPDATE SET debt_ratio = EXCLUDED.debt_ratio, roe = EXCLUDED.roe;
    """

    total_companies = len(companies)
    start_processing = False # 이어하기 스위치
    
    for idx, (corp_code, corp_name) in enumerate(companies, 1):
        
        # 💡 [핵심 복구 2] 루프를 돌다가 선생님이 멈췄던 '팬젠'의 고유코드를 만나면 스위치를 켭니다.
        # [232/401] 휴온스글로벌(00228059) 재무제표 확인 중... 시작
        if corp_code == "00962922":
            start_processing = True

        # 스위치가 켜지기 전(1~141번)까지는 아무것도 안 하고 0.001초 만에 스킵합니다.
        if not start_processing:
            continue
            
        print(f"\n[{idx}/{total_companies}] {corp_name}({corp_code}) 재무제표 확인 중...")
        
        for year, report_code in explicit_targets:
            time.sleep(0.5) 
            params = {"crtfc_key": DART_API_KEY, "corp_code": corp_code, "bsns_year": str(year), "reprt_code": report_code, "fs_div": "CFS"}
            
            try:
                res = requests.get(url, params=params)
                data = res.json()
                status = data.get("status")
                
                if status != "000":
                    params["fs_div"] = "OFS"
                    res = requests.get(url, params=params)
                    data = res.json()
                    status = data.get("status")
                    
                    if status != "000":
                        msg = data.get("message", "데이터 없음")
                        print(f"  -> {year}년 보고서({report_code}) 패스: {msg} (코드: {status})")
                        continue

                account_list = data.get("list", [])
                fs_div = params["fs_div"]

                cursor.execute("DELETE FROM financial_statement WHERE corp_code=%s AND bsns_year=%s AND reprt_code=%s;", (corp_code, year, report_code))

                total_assets = 0
                total_liabilities = 0
                total_equity = 0
                net_income = 0
                valid_data_found = False

                for acnt in account_list:
                    account_nm = acnt.get("account_nm", "").strip()
                    clean_nm = account_nm.replace(" ", "")
                    
                    raw_val = acnt.get("thstrm_amount", "").replace(",", "").strip()
                    
                    try:
                        amount = int(float(raw_val)) if raw_val and raw_val != "-" else 0
                    except ValueError:
                        amount = 0

                    is_target = False
                    if "자산총계" in clean_nm: total_assets = amount; is_target = True
                    elif "부채총계" in clean_nm: total_liabilities = amount; is_target = True
                    elif "자본총계" in clean_nm: total_equity = amount; is_target = True
                    elif clean_nm in ["매출액", "영업수익"]: is_target = True
                    elif "영업이익" in clean_nm: is_target = True
                    elif "당기순이익" in clean_nm or "당기순손익" in clean_nm: net_income = amount; is_target = True
                    elif "영업활동" in clean_nm and "현금흐름" in clean_nm: 
                        account_nm = "영업활동현금흐름"
                        is_target = True

                    if is_target:
                        cursor.execute(fs_insert, (corp_code, year, report_code, fs_div, account_nm, amount))
                        valid_data_found = True

                if not valid_data_found:
                    print(f"  -> {year}년 보고서({report_code}): 타겟 계정과목(자산, 자본 등)을 찾을 수 없음")
                    continue

                debt_ratio = None
                roe = None
                if total_equity != 0:
                    debt_ratio = round((total_liabilities / total_equity) * 100, 2)
                    roe = round((net_income / total_equity) * 100, 2)

                cursor.execute(ratio_upsert, (corp_code, year, report_code, fs_div, debt_ratio, roe))
                conn.commit()
                
                print(f"  ✅ {year}년({report_code}) 제표 적재 및 비율 연산 완료 (부채비율: {debt_ratio}%, ROE: {roe}%)")
                
            except Exception as e:
                print(f"  ❌ 수집 실패 에러: {e}")
                conn.rollback()

    cursor.close()
    conn.close()
    print("\n🎉 모든 기업의 재무제표 수집이 완료되었습니다!")

if __name__ == "__main__":
    collect_financial_statements()