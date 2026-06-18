import os
import json
import psycopg2
import pandas as pd
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
ECOS_API_KEY = os.getenv("ECOS_API_KEY") or os.getenv("API_KEY")

# ==========================================
# 수집 지표 목록 (전 코드 검증 완료)
#
# [업종별 활용 가이드]
# 금융/은행    : 기준금리, 국고채3년, 예금금리, 코스피, 환율, M2
# 반도체/IT   : 환율, 수출금액지수, 코스피, CPI, 경상수지, 뉴스심리지수
# 건설/부동산  : 기준금리, 국고채3년, CPI, 코스피, GDP성장률
# 자동차/제조  : 환율, CPI, 코스피, 수출금액지수, GDP성장률, 실업률, 산업생산
# 에너지/화학  : 환율, 생산자물가, CPI, 코스피, 산업생산, 국제유가(Dubai)
# ==========================================

INDICATORS = {

    # ── 공통 핵심 (전 업종) ──────────────────────────────────

    "한국은행 기준금리": {
        # 722Y001 / 0101000 / D ✅
        "stat_code": "722Y001", "item_code": "0101000", "cycle": "D",
        "sectors": ["금융", "반도체IT", "건설부동산", "자동차제조", "에너지화학"],
    },
    "원/달러 환율": {
        # 731Y001 / 0000001 / D ✅
        "stat_code": "731Y001", "item_code": "0000001", "cycle": "D",
        "sectors": ["금융", "반도체IT", "건설부동산", "자동차제조", "에너지화학"],
    },
    "코스피 지수": {
        # 802Y001 / 0001000 / D ✅
        "stat_code": "802Y001", "item_code": "0001000", "cycle": "D",
        "sectors": ["금융", "반도체IT", "건설부동산", "자동차제조", "에너지화학"],
    },
    "소비자물가지수 (CPI)": {
        # 901Y009 / 0 / M ✅
        "stat_code": "901Y009", "item_code": "0", "cycle": "M",
        "sectors": ["금융", "반도체IT", "건설부동산", "자동차제조", "에너지화학"],
    },
    "실질 GDP 성장률 (전년동기비)": {
        # 200Y102 / 10211 / Q ✅ (실질 원계열 전년동기비)
        "stat_code": "200Y102", "item_code": "10211", "cycle": "Q",
        "sectors": ["금융", "반도체IT", "건설부동산", "자동차제조", "에너지화학"],
    },
    "뉴스심리지수": {
        # 521Y001 / A001 / D ✅
        "stat_code": "521Y001", "item_code": "A001", "cycle": "D",
        "sectors": ["금융", "반도체IT", "건설부동산", "자동차제조", "에너지화학"],
    },
    "실업률": {
        # 901Y027 / I61BB / M ✅
        "stat_code": "901Y027", "item_code": "I61BB", "cycle": "M",
        "sectors": ["금융", "자동차제조", "건설부동산"],
    },

    # ── 금리/금융 ─────────────────────────────────────────────

    "국고채 금리 (3년)": {
        # 817Y002 / 010200000 / D ✅
        "stat_code": "817Y002", "item_code": "010200000", "cycle": "D",
        "sectors": ["금융", "건설부동산"],
    },
    "은행 예금금리 (정기예금)": {
        # 121Y002 / BEABAA211 / M ✅
        "stat_code": "121Y002", "item_code": "BEABAA211", "cycle": "M",
        "sectors": ["금융"],
    },
    "M2 광의통화 (평잔)": {
        # 161Y005 / BBHA00 / M ✅ (현재 계열)
        "stat_code": "161Y005", "item_code": "BBHA00", "cycle": "M",
        "sectors": ["금융"],
    },

    # ── 수출/무역 ─────────────────────────────────────────────

    "수출금액지수": {
        # 403Y001 / *AA / M ✅ (총지수)
        "stat_code": "403Y001", "item_code": "*AA", "cycle": "M",
        "sectors": ["반도체IT", "자동차제조"],
    },
    "경상수지": {
        # 301Y017 / SA000 / M ✅
        "stat_code": "301Y017", "item_code": "SA000", "cycle": "M",
        "sectors": ["반도체IT", "자동차제조"],
    },

    # ── 물가/생산 ─────────────────────────────────────────────

    "생산자물가지수 (총지수)": {
        # 404Y014 / *AA / M ✅
        "stat_code": "404Y014", "item_code": "*AA", "cycle": "M",
        "sectors": ["에너지화학", "자동차제조"],
    },
    "산업생산지수 (제조업)": {
        # 901Y035 / I32A / M ✅
        "stat_code": "901Y035", "item_code": "I32A", "cycle": "M",
        "sectors": ["반도체IT", "자동차제조", "에너지화학"],
    },
    "국제유가 (Dubai)": {
        # 902Y003 / 010102 / M ✅ (달러/배럴)
        "stat_code": "902Y003", "item_code": "010102", "cycle": "M",
        "sectors": ["에너지화학"],
    },

    # ── 대외 ──────────────────────────────────────────────────

    "구매력평가환율 (PPP)": {
        # 902Y019 / KOR / A ✅
        "stat_code": "902Y019", "item_code": "KOR", "cycle": "A",
        "sectors": ["금융"],
    },
}


def get_date_range(cycle: str, end_dt: datetime, begin_dt: datetime) -> tuple[str, str]:
    """주기(cycle)에 맞는 시작/종료 날짜 문자열을 반환합니다."""
    if cycle == "D":
        return begin_dt.strftime("%Y%m%d"), end_dt.strftime("%Y%m%d")
    elif cycle == "M":
        return begin_dt.strftime("%Y%m"), end_dt.strftime("%Y%m")
    elif cycle == "Q":
        return (
            f"{begin_dt.year}Q{(begin_dt.month - 1) // 3 + 1}",
            f"{end_dt.year}Q{(end_dt.month - 1) // 3 + 1}",
        )
    elif cycle == "A":
        return begin_dt.strftime("%Y"), end_dt.strftime("%Y")
    return begin_dt.strftime("%Y%m%d"), end_dt.strftime("%Y%m%d")


def fetch_ecos(stat_code: str, item_code: str, cycle: str,
               start_date: str, end_date: str) -> pd.DataFrame | None:
    """ECOS API에서 데이터를 수집합니다."""
    url = (
        f"http://ecos.bok.or.kr/api/StatisticSearch/"
        f"{ECOS_API_KEY}/json/ko/1/10000/"
        f"{stat_code}/{cycle}/{start_date}/{end_date}/{item_code}/"
    )
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "StatisticSearch" in data:
            df = pd.DataFrame(data["StatisticSearch"]["row"])
            df = df[["TIME", "DATA_VALUE"]].copy()
            df["DATA_VALUE"] = pd.to_numeric(df["DATA_VALUE"], errors="coerce")
            return df.sort_values("TIME").reset_index(drop=True)
        else:
            if "RESULT" in data:
                print(f"  ❌ {data['RESULT']['CODE']} : {data['RESULT']['MESSAGE']}")
            return None
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        return None


def parse_observed_at(time_str: str, cycle: str):
    """ECOS TIME 문자열을 date 객체로 변환합니다."""
    from datetime import date
    try:
        if cycle == "D":
            return datetime.strptime(time_str, "%Y%m%d").date()
        elif cycle == "M":
            return datetime.strptime(time_str, "%Y%m").date().replace(day=1)
        elif cycle == "Q":
            year, q = time_str.split("Q")
            return date(int(year), (int(q) - 1) * 3 + 1, 1)
        elif cycle == "A":
            return date(int(time_str), 1, 1)
    except Exception:
        return None


def collect_macro() -> None:
    """
    ECOS API에서 전 업종 합집합 거시경제 지표를 수집해 raw_macro 테이블에 저장합니다.
    다른 수집기(dart, news)와 동일하게 최근 6개월 기준으로 수집합니다.

    실행:  python datas/macro/collector.py
    .env:  ECOS_API_KEY=...  DATABASE_URL=postgresql://...
    """
    if not ECOS_API_KEY:
        print("ECOS_API_KEY 누락")
        return

    # 다른 수집기와 동일하게 최근 6개월 기준
    end_dt   = datetime.today()
    begin_dt = end_dt - timedelta(days=180)

    print(f"거시경제 데이터 수집 파이프라인 시작 (기간: {begin_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')})...\n")

    # ── DB 연결 (psycopg2 — 다른 수집기와 동일) ──────────────
    try:
        conn   = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return

    insert_sql = """
        INSERT INTO raw_macro (source, indicator_code, observed_at, payload)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (source, indicator_code, observed_at) DO NOTHING;
    """

    total_saved  = 0
    total_failed = []

    for name, info in INDICATORS.items():
        cycle          = info["cycle"]
        stat_code      = info["stat_code"]
        item_code      = info["item_code"]
        indicator_code = f"{stat_code}_{item_code}"
        sectors        = ", ".join(info["sectors"])
        start_date, end_date = get_date_range(cycle, end_dt, begin_dt)

        print(f"[{name}] 수집 중... (업종: {sectors} / 기간: {start_date} ~ {end_date})")

        df = fetch_ecos(stat_code, item_code, cycle, start_date, end_date)

        if df is None or df.empty:
            total_failed.append(name)
            print(f"  ⚠️  수집 실패, 건너뜁니다.\n")
            continue

        # ── DB 저장 ───────────────────────────────────────────
        saved = 0
        try:
            for _, row in df.iterrows():
                time_str    = str(row["TIME"])
                value       = row["DATA_VALUE"]
                observed_at = parse_observed_at(time_str, cycle)
                if observed_at is None:
                    continue

                payload = json.dumps({
                    "name" : name,
                    "time" : time_str,
                    "value": None if pd.isna(value) else float(value),
                    "cycle": cycle,
                }, ensure_ascii=False)

                cursor.execute(insert_sql, ("ECOS", indicator_code, observed_at, payload))
                saved += cursor.rowcount

            conn.commit()
            total_saved += saved
            print(f"  완료: {len(df)}건 수집 / {saved}건 저장 (현재 누적 저장: {total_saved}건)\n")

        except Exception as e:
            conn.rollback()
            total_failed.append(name)
            print(f"  오류 발생 패스 ({name}): {e}\n")
            continue

    print(f"최종 완료: 거시경제 지표 총 {total_saved}건 적재 완료")
    if total_failed:
        print(f"실패 목록: {', '.join(total_failed)}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    collect_macro()