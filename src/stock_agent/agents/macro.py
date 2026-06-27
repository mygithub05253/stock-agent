import os
import psycopg2
from psycopg2 import OperationalError
from datetime import datetime, date
from dotenv import load_dotenv

from stock_agent.agents.fallback import ensure_database_available
from stock_agent.config import get_settings
from stock_agent.schemas.analysis import AgentState, MacroResult, Signal
from stock_agent.tools.macro_tool import get_macro_context, INDICATOR_NAMES

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL") or get_settings().resolved_database_url

# ==========================================
# Single Source of Truth — 지표 이름 상수
# 출처: macro_tool.py의 INDICATOR_NAMES와 완전히 일치
# Key 불일치로 인한 Silent Error 방지
# ==========================================
_K_RATE     = INDICATOR_NAMES["722Y001_0101000"]   # "한국은행 기준금리"
_K_FX       = INDICATOR_NAMES["731Y001_0000001"]   # "원/달러 환율"
_K_KOSPI    = INDICATOR_NAMES["802Y001_0001000"]   # "코스피 지수"
_K_CPI      = INDICATOR_NAMES["901Y009_0"]         # "소비자물가지수 (CPI)"
_K_GDP      = INDICATOR_NAMES["200Y102_10211"]     # "실질 GDP 성장률 (전년동기비)"
_K_NSI      = INDICATOR_NAMES["521Y001_A001"]      # "뉴스심리지수"
_K_OIL      = INDICATOR_NAMES["902Y003_010102"]    # "국제유가 (Dubai)"
_K_PPI      = INDICATOR_NAMES["404Y014_*AA"]       # "생산자물가지수 (총지수)"
_K_INDPROD  = INDICATOR_NAMES["901Y035_I32A"]      # "산업생산지수 (제조업)"

# ==========================================
# DB 연결 실패 시 fallback mock 데이터
# Key는 반드시 위의 상수와 일치해야 함
# ==========================================
_MACRO_FALLBACK: dict[str, float] = {
    _K_RATE:    3.5,
    _K_FX:      1380.0,
    _K_CPI:     2.3,
    _K_GDP:     1.8,
    _K_KOSPI:   2550.0,
    _K_NSI:     100.0,
    _K_OIL:     75.0,
    _K_PPI:     120.0,
    _K_INDPROD: 108.0,
}

# ==========================================
# 섹터별 환율 민감도 보정
# 출처: PLOS ONE (2024) 한국 섹터별 거시경제 영향 연구
# ==========================================
_SECTOR_FX_BONUS: dict[str, int] = {
    "반도체IT":   10,
    "자동차제조":  8,
    "에너지화학":  5,
    "금융":       -5,
    "건설부동산": -3,
}

_SECTOR_RATE_BONUS: dict[str, int] = {
    "금융":        15,
    "반도체IT":   -10,
    "건설부동산": -20,
    "자동차제조":  -8,
    "에너지화학":  -8,
}

# 환율 기준선 (원화 강세/약세 구분)
_FX_BASE = 1200.0  # 역사적 평균 기준선


def _get_value(indicators: dict, name: str) -> float | None:
    """지표 딕셔너리에서 값을 안전하게 추출합니다."""
    entry = indicators.get(name)
    if entry is None:
        return None
    if isinstance(entry, dict):
        return entry.get("value")
    return None


def _normalize_date(raw: object) -> str | None:
    """
    날짜 형식 정규화 — ECOS 포맷 다양성 대응
    출처: ECOS API는 지표별로 날짜 포맷이 다름
      - 연간: "2025"
      - 분기: "2025Q1"
      - 월별: "202505"
      - 일별: "20250501"
      - DB 저장 후: "2025-05-01" (date 객체)
    → 모두 "YYYY-MM-DD" 문자열로 통일
    """
    if raw is None:
        return None
    # date/datetime 객체
    if isinstance(raw, (date, datetime)):
        return raw.strftime("%Y-%m-%d")
    s = str(raw).strip()
    # 이미 YYYY-MM-DD 형식
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s
    # YYYYMMDD 형식
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    # YYYYMM 형식 (월별)
    if len(s) == 6 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-01"
    # YYYY 형식 (연간)
    if len(s) == 4 and s.isdigit():
        return f"{s}-01-01"
    # YYYYQN 형식 (분기)
    if len(s) == 6 and s[4] == "Q":
        q = int(s[5])
        month = (q - 1) * 3 + 1
        return f"{s[:4]}-{month:02d}-01"
    return None


def _calc_roc(
    indicators_current: dict,
    indicators_prev: dict,
    name: str,
    max_days: int = 95,
) -> float | None:
    """
    변화율(Rate of Change) 계산.
    출처: Miyazaki et al. (2026) arXiv:2602.23330

    Args:
        max_days: 두 시점 간격이 이 값을 초과하면 RoC 계산 생략.
                  지표별 발표 주기 불일치로 인한 타임프레임 왜곡 방지.

    TODO Phase 2: 지표별 이종 주기(Heterogeneous Frequency) 정렬
    - 개선: Window Function으로 최신 2개 레코드 단일 쿼리 조회
      + CPI  → YoY(전년동기비) 별도 윈도우
      + GDP  → RoC 계산 생략 (이미 전년동기비 값)
      + 금리 → bp 차이 사용
    """
    cur = _get_value(indicators_current, name)
    prv = _get_value(indicators_prev, name)
    if cur is None or prv is None or prv == 0:
        return None

    # 날짜 정규화 후 간격 체크 (Guard Clause)
    cur_raw = indicators_current.get(name, {}).get("observed_at") if isinstance(indicators_current.get(name), dict) else None
    prv_raw = indicators_prev.get(name, {}).get("observed_at") if isinstance(indicators_prev.get(name), dict) else None
    cur_date = _normalize_date(cur_raw)
    prv_date = _normalize_date(prv_raw)

    if cur_date and prv_date:
        try:
            diff = abs((
                datetime.fromisoformat(cur_date) -
                datetime.fromisoformat(prv_date)
            ).days)
            if diff > max_days:
                return None
        except (ValueError, TypeError):
            return None

    return round((cur - prv) / abs(prv) * 100, 2)


def _fetch_prev_context(conn, sector: str | None, as_of_date: str) -> dict | None:
    """
    RoC 계산을 위한 이전 시점 데이터 조회.
    실패 시 None 반환 → RoC 보정 없이 Level 기반 점수만 사용.

    TODO Phase 2: 지표별 loop 쿼리 → Window Function 단일 쿼리로 교체
    WITH RankedMacro AS (
        SELECT indicator_code, observed_at, payload,
               ROW_NUMBER() OVER (PARTITION BY indicator_code ORDER BY observed_at DESC) as rn
        FROM raw_macro
        WHERE observed_at <= %s AND indicator_code IN (...)
    )
    SELECT * FROM RankedMacro WHERE rn <= 2;
    """
    try:
        from psycopg2.extras import RealDictCursor
        from stock_agent.tools.macro_tool import SECTOR_INDICATORS

        target_codes = SECTOR_INDICATORS.get(sector or "", [
            "722Y001_0101000", "731Y001_0000001",
            "901Y009_0", "200Y102_10211",
        ])

        indicators: dict = {}
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for code in target_codes:
                cur.execute("""
                    SELECT observed_at, payload
                    FROM raw_macro
                    WHERE source = 'ECOS'
                      AND indicator_code = %s
                      AND observed_at < %s
                    ORDER BY observed_at DESC
                    LIMIT 1;
                """, (code, as_of_date))
                row = cur.fetchone()
                name = INDICATOR_NAMES.get(code, code)
                if row:
                    indicators[name] = {
                        "value":       row["payload"].get("value"),
                        "observed_at": _normalize_date(row["observed_at"]),
                    }
                else:
                    indicators[name] = {"value": None, "observed_at": None}
        return {"indicators": indicators}
    except Exception:
        return None


def run_macro(state: AgentState) -> AgentState:
    """
    [Macro Agent] 거시경제 지표를 분석해 투자 환경의 거시적 맥락을 평가합니다.

    - 금리 / 인플레이션 / 경제성장 / 시장 4개 영역 점수화
    - 업종별 환율·금리 민감도 가중치 적용 (비대칭 구조 개선)
    - 변화율(RoC) 추세 보정 (데이터 부족 또는 주기 불일치 시 생략)
    - DB 실패 시 mock fallback으로 파이프라인 유지

    임계값 근거:
        기준금리 2.5% / 3.5% : Yang et al. (2018) Applied Economics 50(7)
        CPI 2.0%             : 한국은행 물가안정목표 (2019~현재)
        CPI 4.0%             : Mishkin (2007) Monetary Policy Strategy
        GDP 2.0%             : IMF World Economic Outlook (2024) 한국 잠재성장률
        GDP 0%               : Miyazaki et al. (2026) arXiv:2602.23330
        NSI 90/110           : 한국은행 뉴스심리지수 기술문서 (2021)
        환율 1350원           : PLOS ONE (2024) 한국 섹터별 거시경제 영향 연구
        환율 1200원 기준선    : 한국은행 환율 역사적 평균 (2000~2024)

    TODO Phase 2:
        1. Z-Score 기반 점수 계산 (절대값 threshold 대신)
        2. 지표별 이종 주기 정렬 쿼리 고도화 (Window Function)
        3. 환율 선형 보정 fx_bonus * (현재환율 - 기준환율) 방식 적용
    """
    # ── 1. 이전 에이전트 결과 확인 ───────────────────────────
    if state.curator is None:
        raise ValueError("Curator result is required before macro analysis")

    sector = state.curator.sector

    # intake.py의 sector명 → macro_tool SECTOR_INDICATORS 키 정규화
    _SECTOR_MAP = {
        "반도체": "반도체IT",
        "IT":     "반도체IT",
        "은행":   "금융",
        "보험":   "금융",
        "증권":   "금융",
        "화학":   "에너지화학",
        "에너지": "에너지화학",
        "자동차": "자동차제조",
        "건설":   "건설부동산",
        "부동산": "건설부동산",
    }
    sector = _SECTOR_MAP.get(sector, sector)

    as_of_date = state.as_of_date
    if not as_of_date:
        as_of_date = datetime.now().strftime("%Y-%m-%d")

    # ── 2. DB 연결 및 macro_tool 호출 ────────────────────────
    fallback_reason: str | None = None
    context: dict | None = None
    prev_context: dict | None = None

    try:
        ensure_database_available()
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=1)
    except (OperationalError, Exception) as exc:
        fallback_reason = f"{exc.__class__.__name__}: {exc}"
    else:
        try:
            context      = get_macro_context(conn, sector=sector, as_of_date=as_of_date)
            prev_context = _fetch_prev_context(conn, sector, as_of_date)
        except Exception as exc:
            fallback_reason = f"macro_tool 호출 실패: {exc}"
        finally:
            conn.close()

    # ── 3. 지표값 결정 (DB 실패 시 fallback) ─────────────────
    if context is None or not context.get("indicators"):
        indicators_raw = {k: {"value": v} for k, v in _MACRO_FALLBACK.items()}
        fallback_reason = fallback_reason or "macro_tool 결과 없음"
    else:
        indicators_raw = context["indicators"]

    def val(name: str) -> float | None:
        return _get_value(indicators_raw, name)

    # ── 4. 점수 계산 ─────────────────────────────────────────
    # 출처: Miyazaki et al. (2026) arXiv:2602.23330 — 4영역 0~100점 구조
    # TODO Phase 2: 절대값 threshold → Z-Score 기반으로 개선
    score   = 50
    reasons: list[str] = []
    risks:   list[str] = []

    # [영역 1] 금리 평가
    # 임계값: Yang et al. (2018) Applied Economics 50(7)
    # 2.5% 이하 = 완화적 통화정책 구간 / 3.5% 이상 = 긴축 구간
    rate = val(_K_RATE)
    if rate is not None:
        if rate <= 2.5:
            score += 15
            reasons.append(f"기준금리({rate}%)가 완화 구간(≤2.5%) 이하로 기업 투자 및 소비 환경이 우호적입니다. [Yang et al., 2018]")
        elif rate >= 3.5:
            score -= 15
            risks.append(f"기준금리({rate}%)가 긴축 구간(≥3.5%)으로 기업 자금 조달 비용이 상승 압력을 받고 있습니다. [Yang et al., 2018]")
        else:
            reasons.append(f"기준금리({rate}%)가 중립 범위(2.5~3.5%)로 통화정책 방향성이 유지되고 있습니다. [Yang et al., 2018]")

    # [영역 2] 인플레이션 평가
    # 임계값: 한국은행 물가안정목표 2.0% (2019~현재)
    #         Mishkin (2007) — CPI 4% 초과 시 긴축 압력 임계값
    cpi = val(_K_CPI)
    if cpi is not None:
        if cpi <= 2.0:
            score += 10
            reasons.append(f"CPI({cpi}%)가 한국은행 물가안정목표(2%) 이하로 통화정책 완화 여지가 있습니다. [한국은행, 2019]")
        elif cpi >= 4.0:
            score -= 15
            risks.append(f"CPI({cpi}%)가 긴축 임계값(≥4%)을 초과해 긴축 통화정책 지속 가능성이 있습니다. [Mishkin, 2007]")
        else:
            reasons.append(f"CPI({cpi}%)가 물가안정목표(2%) 근방으로 안정적 범위(2~4%)에 있습니다. [한국은행, 2019]")

    # [영역 3] 경제성장 평가
    # 임계값: IMF World Economic Outlook (2024) — 한국 잠재성장률 2.0%
    #         Miyazaki et al. (2026) arXiv:2602.23330 — GDP 0% 이하: 침체 리스크
    # GDP 지표는 이미 전년동기비 값이므로 RoC 계산 생략
    gdp = val(_K_GDP)
    if gdp is not None:
        if gdp >= 2.0:
            score += 10
            reasons.append(f"GDP 성장률({gdp}%)이 잠재성장률(2%) 이상으로 기업 실적 개선 기대가 높습니다. [IMF WEO, 2024]")
        elif gdp <= 0:
            score -= 20
            risks.append(f"GDP 성장률({gdp}%)이 0% 이하로 경기 침체 리스크가 존재합니다. [Miyazaki et al., 2026]")
        else:
            reasons.append(f"GDP 성장률({gdp}%)로 잠재성장률(2%) 하회하나 완만한 성장세를 유지하고 있습니다. [IMF WEO, 2024]")

    # [영역 4] 시장 심리 평가
    # 임계값: 한국은행 뉴스심리지수 기술문서 (2021)
    # 100 기준선 / 110 이상: 낙관 구간 / 90 이하: 비관 구간
    nsi = val(_K_NSI)
    if nsi is not None:
        if nsi >= 110:
            score += 5
            reasons.append(f"뉴스심리지수({nsi})가 낙관 구간(≥110)으로 시장 투자심리가 긍정적입니다. [한국은행, 2021]")
        elif nsi <= 90:
            score -= 5
            risks.append(f"뉴스심리지수({nsi})가 비관 구간(≤90)으로 시장 투자심리가 위축되어 있습니다. [한국은행, 2021]")
        else:
            reasons.append(f"뉴스심리지수({nsi})가 중립 범위(90~110)로 시장 심리가 안정적입니다. [한국은행, 2021]")

    # [섹터 가중치] 환율 보정 — 비대칭 구조 개선
    # 임계값: PLOS ONE (2024) 한국 섹터별 거시경제 영향 연구
    # 1350원 이상: 원화 약세 구간 / 1200원 이하: 원화 강세 구간 (역사적 평균)
    # TODO Phase 2: fx_bonus * (현재환율 - 기준환율) 선형 보정으로 개선
    fx = val(_K_FX)
    fx_bonus = _SECTOR_FX_BONUS.get(sector, 0)
    if fx is not None and fx_bonus != 0:
        if fx >= 1350:
            # 원화 약세 구간 → 수출업종 유리, 내수업종 불리
            score += fx_bonus
            if fx_bonus > 0:
                reasons.append(f"원화 약세(환율 {fx}원, ≥1350원 구간)가 {sector} 수출에 유리하게 작용합니다. [PLOS ONE, 2024]")
            else:
                risks.append(f"원화 약세(환율 {fx}원, ≥1350원 구간)가 {sector} 업종 수입 비용 부담으로 작용합니다. [PLOS ONE, 2024]")
        elif fx <= _FX_BASE:
            # 원화 강세 구간 → 방향 반전 적용 (비대칭 개선)
            score -= fx_bonus
            if fx_bonus > 0:
                risks.append(f"원화 강세(환율 {fx}원, ≤1200원 구간)가 {sector} 수출 경쟁력에 부담으로 작용합니다. [PLOS ONE, 2024]")
            else:
                reasons.append(f"원화 강세(환율 {fx}원, ≤1200원 구간)가 {sector} 업종 수입비용 절감에 유리합니다. [PLOS ONE, 2024]")
        else:
            reasons.append(f"환율({fx}원)이 중립 범위(1200~1350원)로 {sector} 업종에 큰 환율 영향은 없습니다. [PLOS ONE, 2024]")

    # [섹터 가중치] 금리 보정
    # 출처: PLOS ONE (2024) 한국 섹터별 거시경제 영향 연구
    rate_bonus = _SECTOR_RATE_BONUS.get(sector, 0)
    if rate is not None and rate_bonus != 0:
        score += rate_bonus
        if rate_bonus > 0:
            reasons.append(f"현 금리 환경({rate}%)이 {sector} 업종에 유리하게 작용합니다. [PLOS ONE, 2024]")
        else:
            risks.append(f"현 금리 환경({rate}%)이 {sector} 업종 수익성에 부담을 줍니다. [PLOS ONE, 2024]")

    # [RoC 보정] 변화율 추세 반영
    # 출처: Miyazaki et al. (2026) arXiv:2602.23330
    rate_of_change: dict[str, float | None] = {}
    if prev_context and prev_context.get("indicators"):
        prev_indicators = prev_context["indicators"]

        # 금리: 비정기 발표 → max_days=200
        roc_rate = _calc_roc(indicators_raw, prev_indicators, _K_RATE, max_days=200)
        # CPI: 월별 → max_days=45
        roc_cpi  = _calc_roc(indicators_raw, prev_indicators, _K_CPI, max_days=45)
        # GDP: 이미 전년동기비 값 → RoC 생략 (성장률의 성장률 방지)
        roc_gdp  = None

        rate_of_change = {
            "기준금리_RoC":  roc_rate,
            "CPI_RoC":       roc_cpi,
            "GDP성장률_RoC": roc_gdp,
        }

        if roc_rate is not None and roc_rate < 0:
            score += 5
            reasons.append(f"기준금리가 하락 추세({roc_rate:+.1f}%)로 통화정책 완화 방향입니다. [Miyazaki et al., 2026]")
        if roc_cpi is not None and roc_cpi > 0:
            score -= 3
            risks.append(f"CPI가 상승 추세({roc_cpi:+.1f}%)로 인플레이션 재가속 가능성이 있습니다. [Miyazaki et al., 2026]")

    # 점수 범위 클리핑
    score = max(0, min(100, score))

    # ── 5. Signal 결정 ────────────────────────────────────────
    if score >= 70:
        macro_signal: Signal = "BUY"
    elif score >= 40:
        macro_signal = "HOLD"
    else:
        macro_signal = "SELL"

    # ── 6. Fallback 경고 추가 ─────────────────────────────────
    if fallback_reason:
        risks.append(
            "DB 연결 실패 fallback: 일부 거시경제 데이터를 일시적으로 불러오지 못해 "
            "보수적 대체 지표로 분석을 계속했습니다."
        )
        risks.append("실제 투자 판단 전 데이터 연결 상태를 확인해 주세요.")

    # ── 7. 사용된 지표값 정리 ─────────────────────────────────
    indicators_out: dict[str, float | None] = {
        name: _get_value(indicators_raw, name)
        for name in indicators_raw
    }

    # ── 8. AgentState 갱신 ───────────────────────────────────
    state.macro = MacroResult(
        score=score,
        macro_signal=macro_signal,
        indicators=indicators_out,
        rate_of_change=rate_of_change,
        reasons=reasons if reasons else ["특별한 거시경제 긍정 신호가 식별되지 않았습니다."],
        risks=risks   if risks   else ["현재 눈에 띄는 거시경제 리스크는 없습니다."],
        sector=sector,
        as_of_date=as_of_date,
    )
    return state
