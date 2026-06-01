from __future__ import annotations

from typing import Any
from psycopg2.extras import RealDictCursor

# ==========================================
# 업종별 지표 매핑
# collector.py의 sectors 필드와 동일하게 맞춤
# ==========================================

SECTOR_INDICATORS: dict[str, list[str]] = {
    "금융":     ["722Y001_0101000", "817Y002_010200000", "121Y002_BEABAA211",
                 "161Y005_BBHS00",  "802Y001_0001000",   "731Y001_0000001"],
    "반도체IT": ["731Y001_0000001", "403Y001_*AA",       "802Y001_0001000",
                 "901Y009_0",       "301Y017_SA000",      "521Y001_A001"],
    "건설부동산":["722Y001_0101000", "817Y002_010200000", "901Y009_0",
                 "802Y001_0001000", "200Y102_10211"],
    "자동차제조":["731Y001_0000001", "901Y009_0",         "802Y001_0001000",
                 "403Y001_*AA",     "200Y102_10211",      "901Y027_I61BB",
                 "901Y035_I32A"],
    "에너지화학":["731Y001_0000001", "404Y014_*AA",       "901Y009_0",
                 "802Y001_0001000", "901Y035_I32A",       "902Y003_010102"],
}

# 지표코드 → 한글 이름 매핑
INDICATOR_NAMES: dict[str, str] = {
    "722Y001_0101000":   "한국은행 기준금리",
    "731Y001_0000001":   "원/달러 환율",
    "802Y001_0001000":   "코스피 지수",
    "901Y009_0":         "소비자물가지수 (CPI)",
    "200Y102_10211":     "실질 GDP 성장률 (전년동기비)",
    "521Y001_A001":      "뉴스심리지수",
    "901Y027_I61BB":     "실업률",
    "817Y002_010200000": "국고채 금리 (3년)",
    "121Y002_BEABAA211": "은행 예금금리 (정기예금)",
    "161Y005_BBHS00":    "M2 광의통화 (평잔)",
    "403Y001_*AA":       "수출금액지수",
    "301Y017_SA000":     "경상수지",
    "404Y014_*AA":       "생산자물가지수 (총지수)",
    "901Y035_I32A":      "산업생산지수 (제조업)",
    "902Y003_010102":    "국제유가 (Dubai)",
    "902Y019_KOR":       "구매력평가환율 (PPP)",
}


def get_macro_context(
    conn,
    sector: str | None = None,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    """
    [macro_tool] raw_macro 테이블에서 거시경제 지표를 조회해 에이전트용 context를 반환합니다.

    Args:
        conn:        psycopg2 DB 커넥션
        sector:      업종 필터 (None이면 전 업종 공통 지표만 반환)
                     "금융" | "반도체IT" | "건설부동산" | "자동차제조" | "에너지화학"
        as_of_date:  기준일 (None이면 오늘 기준 최신값)
                     백테스트 시 "2025-12-01" 형식으로 주입

    Returns:
        {
            "sector":     str,
            "as_of_date": str,
            "indicators": {
                "한국은행 기준금리": {"value": 3.5, "observed_at": "2026-05-01", "cycle": "D"},
                ...
            },
            "summary": str   # LLM 프롬프트에 바로 삽입할 수 있는 요약 문자열
        }
    """
    # ── 조회할 indicator_code 목록 결정 ──────────────────────
    if sector and sector in SECTOR_INDICATORS:
        target_codes = SECTOR_INDICATORS[sector]
    else:
        # sector 없으면 전 업종 공통 6개만
        target_codes = [
            "722Y001_0101000",
            "731Y001_0000001",
            "802Y001_0001000",
            "901Y009_0",
            "200Y102_10211",
            "521Y001_A001",
        ]

    # ── DB 조회: 지표별 기준일 이전 최신값 1건씩 ─────────────
    date_filter = f"AND observed_at <= '{as_of_date}'" if as_of_date else ""

    indicators: dict[str, dict[str, Any]] = {}

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        for code in target_codes:
            query = f"""
                SELECT observed_at, payload
                FROM raw_macro
                WHERE source = 'ECOS'
                  AND indicator_code = %s
                  {date_filter}
                ORDER BY observed_at DESC
                LIMIT 1;
            """
            cur.execute(query, (code,))
            row = cur.fetchone()

            name = INDICATOR_NAMES.get(code, code)

            if row:
                payload = row["payload"]
                indicators[name] = {
                    "value":       payload.get("value"),
                    "observed_at": str(row["observed_at"]),
                    "cycle":       payload.get("cycle"),
                }
            else:
                indicators[name] = {
                    "value":       None,
                    "observed_at": None,
                    "cycle":       None,
                }

    # ── 요약 문자열 생성 (LLM 프롬프트에 삽입용) ─────────────
    summary_lines = [f"[거시경제 지표 요약 — {sector or '전체'} 업종]"]
    for name, data in indicators.items():
        value = data["value"]
        observed = data["observed_at"] or "N/A"
        if value is not None:
            summary_lines.append(f"  - {name}: {value} ({observed} 기준)")
        else:
            summary_lines.append(f"  - {name}: 데이터 없음")

    summary = "\n".join(summary_lines)

    return {
        "sector":     sector or "전체",
        "as_of_date": as_of_date or "최신",
        "indicators": indicators,
        "summary":    summary,
    }