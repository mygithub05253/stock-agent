import os
import io
import time
import zipfile
import requests
import xml.etree.ElementTree as ET
import psycopg2
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dotenv import load_dotenv

# --------------------------------------------------------
# 추가로 적재할 기업 추가 로직
# --------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..")) if "datas" in current_dir else current_dir
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
DART_API_KEY = os.getenv("DART_API_KEY")
krx_id = os.getenv("KRX_ID") or os.getenv("KRX_USER_ID")
krx_pw = os.getenv("KRX_PW") or os.getenv("KRX_PASSWORD")

if krx_id and krx_pw:
    os.environ["KRX_ID"] = krx_id
    os.environ["KRX_PW"] = krx_pw

from pykrx import stock

# 🎯 유저 지정 정밀 타격 대상셋
TARGET_COMPANIES = {
    "005930": "삼성전자",
    "000660": "SK하이닉스"
}

def connect_db():
    return psycopg2.connect(DATABASE_URL)


# --------------------------------------------------------
# 📡 [1탄 미러링] OpenDART 고유코드 맵 다운로드
# --------------------------------------------------------
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


# --------------------------------------------------------
# 🏭 [1탄 미러링] KRX KIND 동적 섹터 탐색
# --------------------------------------------------------
def get_target_sectors_from_krx():
    print("시작: KRX KIND 전 상장사 업종 정보 로드 중...")
    url = 'http://kind.krx.co.kr/corpgeneral/corpList.do'
    params = {'method': 'download', 'searchType': '13'}
    res = requests.get(url, params=params)
    
    dfs = pd.read_html(io.BytesIO(res.content))
    df_krx = dfs[0].copy()
    df_krx['종목코드'] = df_krx['종목코드'].astype(str).str.split('.').str[0].str.zfill(6)
    
    paper_patterns = r'스팩|리츠|기업인수목적|스팩\d+호'
    df_krx = df_krx[~df_krx['회사명'].str.contains(paper_patterns, na=False, regex=True)].copy()
    
    keywords = {
        'semiconductor': ['반도체'],
        'finance': ['은행', '금융', '보험', '증권', '카드'],
        'bio': ['의약', '바이오', '생명공학', '의료용 물질']
    }
    
    def filter_sector_with_override(row):
        stock_code = row['종목코드']
        sector_nm = row['업종']
        
        if stock_code in TARGET_COMPANIES:
            return "반도체"
            
        if not isinstance(sector_nm, str): 
            return None
            
        for key, k_list in keywords.items():
            if any(k in sector_nm for k in k_list): 
                return "반도체" if key == 'semiconductor' else ("금융" if key == 'finance' else "바이오")
        return None

    df_krx.loc[:, 'filtered_sector'] = df_krx.apply(filter_sector_with_override, axis=1)
    df_filtered = df_krx[df_krx['filtered_sector'].notnull()].copy()
    
    df_heavyweights = df_filtered[df_filtered['종목코드'].isin(TARGET_COMPANIES.keys())]
    print(f"완료: 동적 API 조회 및 업종 교정 완료 후 반도체 대장주 {len(df_heavyweights)}곳 매핑 완료")
    return df_heavyweights


# --------------------------------------------------------
# 🚀 [STAGE 1] 1탄 로직: 기업 마스터 정보 동기화 및 6개월 공시 목록 적재
# --------------------------------------------------------
def step1_collect_company_and_reports(cursor, dart_map, df_krx):
    print("\n[STAGE 1] 기업 마스터 동기화 및 6개월 공시 목록 수집 파이프라인 가동...")
    
    company_upsert = """
        INSERT INTO company (corp_code, corp_name, stock_code, sector, listing_date)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (stock_code) DO UPDATE SET
            corp_code = EXCLUDED.corp_code,
            corp_name = EXCLUDED.corp_name,
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
        sector = "반도체" 
        raw_date = row['상장일']
        listing_date = raw_date.split()[0] if isinstance(raw_date, str) else None

        if stock_code in dart_map:
            corp_code = dart_map[stock_code]
            cursor.execute(company_upsert, (corp_code, corp_name, stock_code, sector, listing_date))
            valid_companies.append((corp_code, corp_name, stock_code))
            
    print(f"DB 마스터 동기화 완료: {len(valid_companies)}개 대장주 등록 및 갱신")

    end_date = datetime.today()
    begin_date = end_date - timedelta(days=180)
    bgn_de = begin_date.strftime("%Y%m%d")
    end_de = end_date.strftime("%Y%m%d")

    url = "https://opendart.fss.or.kr/api/list.json"
    total_reports = 0

    for corp_code, corp_name, stock_code in valid_companies:
        print(f"  -> {corp_name} 6개월 공시 목록 실시간 호출 중...")
        time.sleep(0.5)
        params = {
            "crtfc_key": DART_API_KEY, "corp_code": corp_code,
            "bgn_de": bgn_de, "end_de": end_de,
            "page_no": "1", "page_count": "100"
        }

        try:
            res = requests.get(url, params=params)
            data = res.json()
            if data.get("status") != "000": continue

            for rep in data.get("list", []):
                cursor.execute(report_insert, (rep.get("rcept_no"), corp_code, rep.get("report_nm"), rep.get("rcept_dt")))
                total_reports += 1
        except Exception as e:
            print(f"  ❌ 공시 메타 적재 오류 패스 ({corp_name}): {e}")
            continue

    print(f"✅ STAGE 1 완료: 반도체 대장주 공시 메타데이터 {total_reports}건 적재 완료")
    return valid_companies


# --------------------------------------------------------
# 🚀 [STAGE 2] 2탄 로직: 최신 6개월 주가, 퀀트, 수급, 공매도 시계열 적재
# --------------------------------------------------------
def step2_collect_stock_prices(cursor, valid_companies):
    print("\n[STAGE 2] 6개월 고속화 퀀트/수급/공매도 통합 시계열 수집 가동...")
    
    end_date = datetime.today()
    begin_date = end_date - timedelta(days=180)
    default_start_str, default_end_str = begin_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")

    insert_query = """
        INSERT INTO stock_price (
            stock_code, base_date, close_price, market_cap, volume, 
            per, pbr, dividend_yield, foreign_net_buy, institutional_net_buy, short_ratio
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (stock_code, base_date) 
        DO UPDATE SET 
            close_price = EXCLUDED.close_price, market_cap = EXCLUDED.market_cap, volume = EXCLUDED.volume,
            per = EXCLUDED.per, pbr = EXCLUDED.pbr, dividend_yield = EXCLUDED.dividend_yield,
            foreign_net_buy = EXCLUDED.foreign_net_buy, institutional_net_buy = EXCLUDED.institutional_net_buy,
            short_ratio = EXCLUDED.short_ratio;
    """

    for corp_code, corp_name, stock_code in valid_companies:
        print(f"  -> {corp_name} ({stock_code}) 122개 상당 영업일 통합 지표 결합 중...")
        try:
            time.sleep(1.5) 
            df_ohlcv = stock.get_market_ohlcv_by_date(default_start_str, default_end_str, stock_code)
            df_cap = stock.get_market_cap_by_date(default_start_str, default_end_str, stock_code)
            
            if df_ohlcv is None or df_ohlcv.empty: continue

            real_start_str = df_ohlcv.index[0].strftime("%Y%m%d")
            real_end_str = df_ohlcv.index[-1].strftime("%Y%m%d")
            df_total = df_ohlcv[['종가', '거래량']].join(df_cap['시가총액'], how='left')

            try:
                df_fund = stock.get_market_fundamental_by_date(real_start_str, real_end_str, stock_code)
                if df_fund is not None and not df_fund.empty:
                    df_total = df_total.join(df_fund[[c for c in ['PER', 'PBR', 'DIV'] if c in df_fund.columns]], how='left')
            except Exception: pass

            try:
                df_trading = stock.get_market_trading_value_by_date(real_start_str, real_end_str, stock_code)
                if df_trading is not None and not df_trading.empty:
                    df_total = df_total.join(df_trading[[c for c in ['외국인합계', '기관합계'] if c in df_trading.columns]], how='left')
            except Exception: pass

            try:
                df_short = stock.get_shorting_volume_by_date(real_start_str, real_end_str, stock_code)
                if df_short is not None and not df_short.empty:
                    s_col = next((c for c in ['비중', '공매도비중'] if c in df_short.columns), None)
                    if s_col: df_total = df_total.join(df_short[[s_col]].rename(columns={s_col: '비중'}), how='left')
            except Exception: pass

            df_total = df_total.replace([np.nan, np.inf, -np.inf], None)
            inserted_count = 0
            
            for date, row in df_total.iterrows():
                r = row.to_dict()
                cursor.execute(insert_query, (
                    stock_code, date.strftime('%Y-%m-%d'),
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
            print(f"  ✅ {corp_name} 시계열 투자 지표 총 {inserted_count}건 완벽 가동")
        except Exception as e:
            print(f"  ❌ {corp_name} 시세 레이어 수집 실패 패스: {e}")
            continue


# --------------------------------------------------------
# 🚀 [STAGE 3] 3탄 로직: 버그 완벽 수정본 (IFRS 계정 표준 ID 기반 매핑)
# --------------------------------------------------------
def step3_collect_financial_statements(cursor, valid_companies):
    print("\n[STAGE 3] 지정 5대 타겟 분기/연간 재무제표 및 비율 연산 적재 가동 (IFRS ID 보정 적용)...")
    
    explicit_targets = [
        (2025, "11013"), (2025, "11012"), (2025, "11014"), (2025, "11011"), (2026, "11013")
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

    # 💡 [핵심 교정 정교화] 대기업 분기별 고유 매핑 한글 명칭 유도 테이블
    STANDARD_TARGET_ACCOUNTS = {
        "자산총계": ["자산총계", "자산 총계"],
        "부채총계": ["부채총계", "부채 총계"],
        "자본총계": ["자본총계", "자본 총계"],
        "매출액": ["매출액", "영업수익", "수익(매출액)"],
        "영업이익": ["영업이익", "영업이익(손실)"],
        "당기순이익": ["당기순이익", "당기순이익(손실)", "분기순이익", "반기순이익", "연결당기순이익"]
    }

    for corp_code, corp_name, _ in valid_companies:
        print(f"  -> {corp_name}({corp_code}) 국세청 제출 원천 계정 분석 중...")
        for year, report_code in explicit_targets:
            time.sleep(0.6) 
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
                    if status != "000": continue

                account_list = data.get("list", [])
                fs_div = params["fs_div"]
                
                # 중복 충돌 방지를 위해 기존 이 연도/보고서 계정 초기 청소
                cursor.execute("DELETE FROM financial_statement WHERE corp_code=%s AND bsns_year=%s AND reprt_code=%s;", (corp_code, year, report_code))

                total_assets, total_liabilities, total_equity, net_income = 0, 0, 0, 0
                valid_data_found = False
                extracted_data = {}

                for acnt in account_list:
                    account_nm = acnt.get("account_nm", "").strip()
                    clean_nm = account_nm.replace(" ", "")
                    raw_val = acnt.get("thstrm_amount", "").replace(",", "").strip()
                    account_id = acnt.get("account_id", "").strip() # OpenDART 고유 표준 ID 추출
                    
                    try: amount = int(float(raw_val)) if raw_val and raw_val != "-" else 0
                    except ValueError: amount = 0

                    matched_standard_name = None
                    
                    # 💡 1차 가드레일: 공식 표준 ID 기반 정밀 타격 매핑 (이름 중복 덮어쓰기 버그 완전 철폐)
                    if account_id == "ifrs-full_Assets": matched_standard_name = "자산총계"
                    elif account_id == "ifrs-full_Liabilities": matched_standard_name = "부채총계"
                    elif account_id == "ifrs-full_Equity": matched_standard_name = "자본총계"
                    elif account_id in ["ifrs-full_Revenue", "ifrs-full_GrossProfit"]: matched_standard_name = "매출액"
                    elif account_id == "ifrs-full_OperatingProfitLoss": matched_standard_name = "영업이익"
                    elif account_id in ["ifrs-full_ProfitLoss", "ifrs-full_ProfitLossFromContinuingOperations"]: 
                        matched_standard_name = "당기순이익"

                    # 2차 백업: ID가 비표준형일 경우 유도 딕셔너리 정밀 검사
                    if not matched_standard_name:
                        for std_name, aliases in STANDARD_TARGET_ACCOUNTS.items():
                            if any(alias == clean_nm or alias in account_nm for alias in aliases):
                                # 단, 당기순이익의 경우 '총포괄'이나 '비지배'가 들어간 리스크 행은 건너뜀
                                if std_name == "당기순이익" and any(k in clean_nm for k in ["총포괄", "비지배", "기타"]):
                                    continue
                                matched_standard_name = std_name
                                break

                    if matched_standard_name:
                        # 분기보고서 누적 데이터 왜곡을 방지하기 위해 중복 인입 시 양수 금액을 우선 배정
                        if matched_standard_name in extracted_data and extracted_data[matched_standard_name] > 0 and amount == 0:
                            continue
                        extracted_data[matched_standard_name] = amount

                # 실제 변수들에 값 이식
                total_assets = extracted_data.get("자산총계", 0)
                total_liabilities = extracted_data.get("부채총계", 0)
                total_equity = extracted_data.get("자본총계", 0)
                net_income = extracted_data.get("당기순이익", 0)

                # 최종 정제된 6대 항목을 DB에 적재
                for std_nm, amount in extracted_data.items():
                    cursor.execute(fs_insert, (corp_code, year, report_code, fs_div, std_nm, amount))
                    valid_data_found = True

                if valid_data_found and total_equity > 0:
                    debt_ratio = round((total_liabilities / total_equity) * 100, 2)
                    
                    # 💡 [보정 가이드 반영] 삼성전자/하이닉스 분기 보고서(1분기, 반기, 3분기) 당기순이익은 
                    # 연간 환산(Annualized) 처리를 해주어야 온전한 분기 ROE 지표가 정상 표출됩니다.
                    annualized_net_income = net_income
                    if report_code == "11013": annualized_net_income = net_income * 4     # 1분기 * 4
                    elif report_code == "11012": annualized_net_income = net_income * 2   # 반기 * 2
                    elif report_code == "11014": annualized_net_income = int(net_income * (4 / 3)) # 3분기 누적 환산
                    
                    roe = round((annualized_net_income / total_equity) * 100, 2)
                    
                    cursor.execute(ratio_upsert, (corp_code, year, report_code, fs_div, debt_ratio, roe))
                    
            except Exception as e:
                print(f"     ❌ {year}년({report_code}) 재무제표 처리 에러 패스: {e}")
        print(f"  ✅ {corp_name} 5대 타겟 재무 제표 및 재무비율 연산 보정 완료")


# --------------------------------------------------------
# 🚀 [STAGE 4] 4탄 로직: RAG 임베딩용 공시 원문 텍스트 압축 파싱
# --------------------------------------------------------
def step4_collect_disclosure_contents(cursor, valid_companies):
    print("\n[STAGE 4] RAG 지식 저장소 구축용 공시 원문 텍스트 마이닝 가동...")
    
    end_date = datetime.today()
    begin_date = end_date - timedelta(days=180)
    target_date_str = begin_date.strftime("%Y%m%d")

    corp_codes = [c[0] for c in valid_companies]
    cursor.execute("""
        SELECT dr.rcept_no, dr.report_nm 
        FROM disclosure_report dr
        LEFT JOIN disclosure_content dc ON dr.rcept_no = dc.rcept_no
        WHERE dc.rcept_no IS NULL
          AND dr.rcept_dt >= %s
          AND dr.corp_code IN %s;
    """, (target_date_str, tuple(corp_codes)))
    
    target_reports = cursor.fetchall()
    if not target_reports:
        print("  ✅ 모든 공시 보고서의 원문 텍스트가 이미 최신화 상태입니다.")
        return

    url = "https://opendart.fss.or.kr/api/document.xml"
    insert_query = """
        INSERT INTO disclosure_content (rcept_no, content, summary)
        VALUES (%s, %s, %s)
        ON CONFLICT (rcept_no) DO UPDATE SET content = EXCLUDED.content, updated_at = NOW();
    """

    success_count = 0
    for rcept_no, report_nm in target_reports:
        time.sleep(0.5)
        try:
            res = requests.get(url, params={"crtfc_key": DART_API_KEY, "rcept_no": rcept_no})
            if not zipfile.is_zipfile(io.BytesIO(res.content)): continue

            with zipfile.ZipFile(io.BytesIO(res.content)) as z:
                file_list = z.namelist()
                if not file_list: continue
                
                raw_xml = z.read(file_list[0])
                soup = BeautifulSoup(raw_xml, "lxml-xml")
                clean_text = soup.get_text("\n", strip=True)
                
                if clean_text.strip():
                    cursor.execute(insert_query, (rcept_no, clean_text, None))
                    success_count += 1
        except Exception:
            continue
            
    print(f"✅ STAGE 4 완료: 신규 공시 원문 총 {success_count}건의 텍스트 데이터 이식 완공")


# --------------------------------------------------------
# 🔗 메인 오케스트레이터 가동
# --------------------------------------------------------
def main():
    if not DART_API_KEY or not DATABASE_URL:
        print("❌ [CRITICAL] 환경 변수 세팅 누락")
        return

    try:
        conn = connect_db()
        cursor = conn.cursor()
    except Exception as e:
        print(f"DB 연결 에러: {e}")
        return

    try:
        dart_map = get_dart_corp_code_map()
        df_krx = get_target_sectors_from_krx()

        # [1] 1탄 연동: 마스터 정보 및 6개월 공시 목록
        valid_companies = step1_collect_company_and_reports(cursor, dart_map, df_krx)
        conn.commit()

        if valid_companies:
            # [2] 2탄 연동: 6개월 주가 수급 공매도 시계열 대량 적재
            step2_collect_stock_prices(cursor, valid_companies)
            conn.commit()

            # [3] 3탄 연동: 다중 재무제표 무결성 이식 및 비율 연산 (보정 완료)
            step3_collect_financial_statements(cursor, valid_companies)
            conn.commit()

            # [4] 4탄 연동: RAG용 공시 XML 원천 본문 파싱
            step4_collect_disclosure_contents(cursor, valid_companies)
            conn.commit()

        print("\n==================================================")
        print("🎉 [SUCCESS] 삼전/하이닉스 대장주 파이프라인이 보정된 IFRS 규칙으로 완벽 적재되었습니다!")
        print("==================================================")

    except Exception as e:
        conn.rollback()
        print(f"❌ 통합 파이프라인 구동 실패: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()