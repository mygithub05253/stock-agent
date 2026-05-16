import os
import requests
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DART_API_KEY = os.getenv("DART_API_KEY")

def collect_dart() -> None:
    """DART API 데이터를 가져와 고유 관계를 고려하여 Core 테이블에 다이렉트로 적재합니다."""
    if not DART_API_KEY:
        print("❌ 에러: .env 파일에 DART_API_KEY가 설정되지 않았습니다.")
        return

    # [Step 1] 날짜 범위 설정 (최근 3개월)
    end_date = datetime.today()
    begin_date = end_date - timedelta(days=89)
    
    bgn_de = begin_date.strftime("%Y%m%d")
    end_de = end_date.strftime("%Y%m%d")
    
    print(f"📡 OpenDART 실시간 파싱 및 적재 시작: {begin_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")

    # [Step 2] OpenDART API 호출
    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "page_count": 100,
        "page_no": 1
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ API 요청 중 오류 발생: {e}")
        return
        
    if data.get("status") != "000":
        print(f"❌ DART API 에러 메시지: {data.get('message')}")
        return

    report_list = data.get("list", [])
    print(f"📦 분석할 공시 내역 목록: {len(report_list)}건")

    # [Step 3] Supabase 연결 및 트랜잭션 처리
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        return
    
    # 1단계: 마스터 정보 저장
    company_upsert_query = """
        INSERT INTO company (corp_code, stock_code, corp_name)
        VALUES (%s, %s, %s)
        ON CONFLICT (corp_code) 
        DO UPDATE SET 
            corp_name = EXCLUDED.corp_name,
            stock_code = COALESCE(company.stock_code, EXCLUDED.stock_code);
    """
    
    # 2단계: 목차 정보 저장
    report_upsert_query = """
        INSERT INTO disclosure_report (rcept_no, corp_code, report_nm, rcept_dt)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (rcept_no) 
        DO UPDATE SET 
            report_nm = EXCLUDED.report_nm,
            rcept_dt = EXCLUDED.rcept_dt;
    """
    
    try:
        success_count = 0
        for item in report_list:
            raw_stock_code = item.get("stock_code")
            stock_code = raw_stock_code.strip() if raw_stock_code and raw_stock_code.strip() else None
            
            rcept_dt = item.get("rcept_dt")
            formatted_date = f"{rcept_dt[:4]}-{rcept_dt[4:6]}-{rcept_dt[6:]}"
            
            # 1. 상위 테이블인 company 데이터 먼저 밀어넣기
            cursor.execute(company_upsert_query, (
                item.get("corp_code"),
                stock_code,
                item.get("corp_name")
            ))
            
            # 2. 하위 테이블인 disclosure_report 데이터 밀어넣기
            cursor.execute(report_upsert_query, (
                item.get("rcept_no"),
                item.get("corp_code"),
                item.get("report_nm"),
                formatted_date
            ))
            success_count += 1
            
        conn.commit()
        print(f"✅ {success_count}건의 공시 마스터 및 레포트 정보가 Supabase에 다이렉트로 완벽하게 저장되었습니다.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 데이터베이스 파싱 처리 중 에러 발생: {e}")
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    collect_dart()