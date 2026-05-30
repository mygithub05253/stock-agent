import os
import io
import time
import zipfile
import requests
import xml.etree.ElementTree as ET
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
DART_API_KEY = os.getenv("DART_API_KEY")

def get_dart_corp_code_map():
    print("시작: OpenDART 고유코드 매핑 데이터 다운로드 중...")
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    params = {"crtfc_key": DART_API_KEY}
    
    res = requests.get(url, params=params)
    if not zipfile.is_zipfile(io.BytesIO(res.content)):
        print("실패: 올바른 고유코드 파일 형식이 아닙니다.")
        return {}
        
    corp_map = {}
    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
        xml_data = z.read("CORPCODE.xml")
        root = ET.fromstring(xml_data)
        for corp in root.findall("list"):
            stock_code = corp.find("stock_code").text.strip()
            corp_code = corp.find("corp_code").text.strip()
            if stock_code:
                corp_map[stock_code] = corp_code
    print(f"완료: {len(corp_map)}개 기업 매핑 테이블 준비 완료")
    return corp_map

def get_target_sectors_from_krx():
    print("시작: KRX KIND 전 상장사 업종 정보 로드 중...")
    url = 'http://kind.krx.co.kr/corpgeneral/corpList.do'
    params = {'method': 'download', 'searchType': '13'}
    res = requests.get(url, params=params)
    
    dfs = pd.read_html(io.BytesIO(res.content))
    df_krx = dfs[0]
    df_krx['종목코드'] = df_krx['종목코드'].astype(str).str.split('.').str[0].str.zfill(6)
    
    # 💡 [핵심 추가] 스팩(SPAC), 리츠, 기업인수목적 등 페이퍼 컴퍼니 원천 차단
    initial_count = len(df_krx)
    paper_patterns = '스팩|리츠|기업인수목적|스팩\d+호'
    df_krx = df_krx[~df_krx['회사명'].str.contains(paper_patterns, na=False, regex=True)]
    print(f"필터링: 페이퍼 컴퍼니 제외됨 (전체 상장사 {initial_count}개 -> {len(df_krx)}개)")
    
    keywords = {
        'semiconductor': ['반도체'],
        'finance': ['은행', '금융', '보험', '증권', '카드'],
        'bio': ['의약', '바이오', '생명공학', '의료용 물질']
    }
    
    def filter_sector(sector_nm):
        if not isinstance(sector_nm, str):
            return None
        for key, k_list in keywords.items():
            if any(k in sector_nm for k in k_list):
                return sector_nm
        return None

    df_krx['filtered_sector'] = df_krx['업종'].apply(filter_sector)
    df_filtered = df_krx[df_krx['filtered_sector'].notnull()]
    print(f"완료: 타겟 섹터(반도체, 금융, 바이오) 발견 기업 수: {len(df_filtered)}곳")
    return df_filtered


def collect_company_and_reports():
    print("지정 섹터 최근 6개월 타겟 수집 파이프라인 시작...")
    if not DART_API_KEY:
        print("DART_API_KEY 누락")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return

    dart_map = get_dart_corp_code_map()
    df_krx = get_target_sectors_from_krx()

    company_upsert = """
        INSERT INTO company (corp_code, corp_name, stock_code, sector, listing_date)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (corp_code) DO UPDATE SET
            sector = EXCLUDED.sector,
            listing_date = EXCLUDED.listing_date;
    """
    
    report_insert = """
        INSERT INTO disclosure_report (rcept_no, corp_code, report_nm, rcept_dt)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (rcept_no) DO NOTHING;
    """

    valid_companies = []
    for _, row in df_krx.iterrows():
        stock_code = row['종목코드']
        corp_name = row['회사명']
        sector = row['업종']
        raw_date = row['상장일']
        listing_date = raw_date.split()[0] if isinstance(raw_date, str) else None

        if stock_code in dart_map:
            corp_code = dart_map[stock_code]
            cursor.execute(company_upsert, (corp_code, corp_name, stock_code, sector, listing_date))
            valid_companies.append((corp_code, corp_name))
            
    conn.commit()
    print(f"DB 마스터 동기화 완료: {len(valid_companies)}개 기업 등록됨")

    end_date = datetime.today()
    begin_date = end_date - timedelta(days=180) # 6개월 수정
    bgn_de = begin_date.strftime("%Y%m%d")
    end_de = end_date.strftime("%Y%m%d")

    url = "https://opendart.fss.or.kr/api/list.json"
    total_reports = 0
    total_companies = len(valid_companies)

    print(f"공시 목록 수집 시작 (기간: {begin_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')})")

    for idx, (corp_code, corp_name) in enumerate(valid_companies, 1):
        print(f"[{idx}/{total_companies}] {corp_name} 6개월 공시 목록 가져오는 중... (현재 누적 공시: {total_reports}건)")
        
        time.sleep(0.5)
        params = {
            "crtfc_key": DART_API_KEY,
            "corp_code": corp_code,
            "bgn_de": bgn_de,
            "end_de": end_de,
            "page_no": "1",
            "page_count": "100"
        }

        try:
            res = requests.get(url, params=params)
            data = res.json()
            
            if data.get("status") != "000":
                continue

            report_list = data.get("list", [])
            for rep in report_list:
                rcept_no = rep.get("rcept_no")
                report_nm = rep.get("report_nm")
                rcept_dt = rep.get("rcept_dt")

                cursor.execute(report_insert, (rcept_no, corp_code, report_nm, rcept_dt))
                total_reports += 1
                
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"오류 발생 패스 ({corp_name}): {e}")
            continue

    print(f"최종 완료: 타겟 섹터 기업의 공시 메타데이터 총 {total_reports}건 적재 완료")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    collect_company_and_reports()