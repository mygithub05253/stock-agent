import os
import time
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
DART_API_KEY = os.getenv("DART_API_KEY")

def collect_financial_statements():
    print("전체 재무제표 수집 및 파생 비율 연산 파이프라인 시작...")
    
    if not DART_API_KEY:
        print("DART_API_KEY 누락")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute("SELECT corp_code, corp_name FROM company;")
        companies = cursor.fetchall()
    except Exception as e:
        print(f"DB 연결 및 조회 실패: {e}")
        return

    target_years = [2023, 2024, 2025]
    report_code = "11011" #사업보고서(1년 결산 보고서)고유코드. 1분기 보고서는 11013, 반기보고서는 11012, 3분기 보고서는 11014
    url = "https://opendart.fss.or.kr/api/fnlttAcntAll.json" # 재무제표 전체 행 조회 API

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

    for corp_code, corp_name in companies:
        for year in target_years:
            time.sleep(0.5)
            params = {"crtfc_key": DART_API_KEY, "corp_code": corp_code, "bsns_year": str(year), "reprt_code": report_code, "fs_div": "CFS"}
            
            try:
                res = requests.get(url, params=params)
                data = res.json()
                if data.get("status") != "000":
                    params["fs_div"] = "OFS"
                    res = requests.get(url, params=params)
                    data = res.json()
                    if data.get("status") != "000":
                        continue

                account_list = data.get("list", [])
                fs_div = params["fs_div"]

                cursor.execute("DELETE FROM financial_statement WHERE corp_code=%s AND bsns_year=%s AND reprt_code=%s;", (corp_code, year, report_code))

                total_assets = 0
                total_liabilities = 0
                total_equity = 0
                net_income = 0

                for acnt in account_list:
                    account_nm = acnt.get("account_nm", "").strip()
                    clean_nm = account_nm.replace(" ", "")
                    
                    raw_val = acnt.get("thstrm_amount", "").replace(",", "").strip()
                    amount = int(raw_val) if raw_val and raw_val != "-" else 0

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

                debt_ratio = None
                roe = None
                if total_equity != 0:
                    debt_ratio = round((total_liabilities / total_equity) * 100, 2)
                    roe = round((net_income / total_equity) * 100, 2)

                cursor.execute(ratio_upsert, (corp_code, year, report_code, fs_div, debt_ratio, roe))
                conn.commit()
                print(f"[{corp_name}] {year}년 전체 제표 적재 및 파생 비율 연산 완료")
                
            except Exception as e:
                print(f"[{corp_name}] 수집 실패 패스: {e}")
                conn.rollback()

    cursor.close()
    conn.close()

if __name__ == "__main__":
    collect_financial_statements()