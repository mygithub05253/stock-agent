import os
import psycopg2
from psycopg2 import OperationalError
from datetime import datetime
from dotenv import load_dotenv

from stock_agent.schemas.analysis import AgentState, MacroResult, Signal
from stock_agent.tools.macro_tool import get_macro_context

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# ==========================================
# DB 연결 실패 시 fallback mock 데이터
# (다른 에이전트와 동일한 패턴)
# ==========================================
_MACRO_FALLBACK: dict[str, float] = {
    "한국은행 기준금리":         3.5,
    "원/달러 환율":              1380.0,
    "소비자물가지수 (CPI)":      2.3,
    "실질 GDP 성장률 (전년동기비)": 1.8,
    "코스피 지수":               2550.0,
    "뉴스심리지수":              100.0,
    "국고채 금리 (3년)":         3.8,
    "생산자물가지수 (총지수)":   120.0,
    "산업생산지수 (제조업)":     108.0,
    "수출금액지수":              112.0,
    "국제유가 (Dubai)":          75.0,
}

# ==========================================
# 섹터별 환율 민감도 보정
# 출처: PLOS ONE (2024) 한국 섹터별 거시경제 영향 연구
# ==========================================
_SECTOR_FX_BONUS: dict[str, int] = {
    "반도체IT":   10,   # 원화약세 → 수출 유리
    "자동차제조":  8,   # 원화약세 → 수출 유리
    "에너지화학":  5,   # 원화약세 → 일부 유리
    "금융":       -5,   # 원화약세 → 수입비용 증가
    "건설부동산": -3,   # 원화약세 → 외자 조달 불리
}

_SECTOR_RATE_BONUS: dict[str, int] = {
    "금융":        15,  # 금리↑ → 예대마진 확대
    "반도체IT":   -10,  # 금리↑ → 성장주 할인율 상승
    "건설부동산": -20,  # 금리↑ → 대출 수요 급감
    "자동차제조":  -8,  # 금리↑ → 할부 수요 감소
    "에너지화학":  -8,  # 금리↑ → 설비투자 위축
}


def _get_value(indicators: dict, name: str) -> float | None:
    """지표 딕셔너리에서 값을 안전하게 추출합니다."""
    entry = indicators.get(name)
    if entry is None:
        return None
    if isinstance(entry, dict):
        return entry.get("value")
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
                  기본값 95일 = 분기(90일) + 여유 5일.
                  지표별 발표 주기 불일치로 인한 타임프레임 왜곡 방지.

    TODO Phase 2: 지표별 이종 주기(Heterogeneous Frequency) 정렬
    - 현재: 단순 직전값 대비 RoC (주기 불일치 문제 있음)
    - 개선: Window Function으로 최신 2개 레코드 단일 쿼리 조회
      + CPI  → YoY(전년동기비) 별도 윈도우
      + GDP  → RoC 계산 생략 (이미 전년동기비 값)
      + 금리 → bp 차이 사용
    - Issue: "매크로 지표별 이종 주기 정렬을 위한 쿼리 고도화"
    """
    cur = _get_value(indicators_current, name)
    prv = _get_value(indicators_prev, name)
    if cur is None or prv is None or prv == 0:
        return None

    # 날짜 간격 체크 — 주기 불일치 방지 (Guard Clause)
    cur_date = indicators_current.get(name, {}).get("observed_at") if isinstance(indicators_current.get(name), dict) else None
    prv_date = indicators_prev.get(name, {}).get("observed_at") if isinstance(indicators_prev.get(name), dict) else None
    if cur_date and prv_date:
        try:
            diff = abs((
                datetime.fromisoformat(str(cur_date)) -
                datetime.fromisoformat(str(prv_date))
            ).days)
            if diff > max_days:
                return None  # 간격 초과 → RoC 계산 생략
        except (ValueError, TypeError):
            return None

    return round((cur - prv) / abs(prv) * 100, 2)


def _fetch_prev_context(conn, sector: str | None, as_of_date: str) -> dict | None:
    """
    RoC 계산을 위한 이전 시점 데이터 조회.
    실패 시 None 반환 → RoC 보정 없이 Level 기반 점수만 사용.

    TODO Phase 2: 현재 지표별 loop 쿼리 → Window Function 단일 쿼리로 교체
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
        from stock_agent.tools.macro_tool import SECTOR_INDICATORS, INDICATOR_NAMES

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
                        "observed_at": str(row["observed_at"]),
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
    - 업종별 환율·금리 민감도 가중치 적용
    - 변화율(RoC) 추세 보정 (데이터 부족 또는 주기 불일치 시 생략)
    - DB 실패 시 mock fallback으로 파이프라인 유지

    논문 근거:
        Miyazaki et al. (2026). arXiv:2602.23330
        Yang et al. (2018). Applied Economics 50(7)
        PLOS ONE (2024). 한국 섹터별 거시경제 영향

    TODO Phase 2:
        1. Z-Score 기반 점수 계산 (절대값 threshold 대신)
           - 최근 3년 시계열 기준 Z-Score 반영
           - get_macro_history() 함수 추가 필요
        2. 지표별 이종 주기 정렬 쿼리 고도화
           - Window Function 단일 쿼리로 레이턴시 개선
           - CPI(YoY), GDP(RoC 생략), 금리(bp 차이) 별도 처리
    """
    # ── 1. 이전 에이전트 결과 확인 ───────────────────────────
    if state.curator is None:
        raise ValueError("Curator result is required before macro analysis")

    sector = state.curator.sector

    as_of_date = state.as_of_date
    if not as_of_date:
        as_of_date = datetime.now().strftime("%Y-%m-%d")

    # ── 2. DB 연결 및 macro_tool 호출 ────────────────────────
    fallback_reason: str | None = None
    context: dict | None = None
    prev_context: dict | None = None

    try:
        conn = psycopg2.connect(DATABASE_URL)
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
    # 출처: Miyazaki et al. (2026) 4영역 0~100점 구조
    # TODO Phase 2: 절대값 threshold → Z-Score 기반으로 개선
    score   = 50
    reasons: list[str] = []
    risks:   list[str] = []

    # [영역 1] 금리 평가
    # 출처: Yang et al. (2018) — 금리↑ = 주가↓
    rate = val("한국은행 기준금리")
    if rate is not None:
        if rate <= 2.5:
            score += 15
            reasons.append(f"기준금리({rate}%)가 낮아 기업 투자 및 소비 환경이 우호적입니다.")
        elif rate >= 3.5:
            score -= 15
            risks.append(f"기준금리({rate}%)가 높아 기업 자금 조달 비용이 상승 압력을 받고 있습니다.")

    # [영역 2] 인플레이션 평가
    # 출처: Miyazaki et al. (2026) — 안정적 인플레이션 = 긍정
    cpi = val("소비자물가지수 (CPI)")
    if cpi is not None:
        if cpi <= 2.0:
            score += 10
            reasons.append(f"CPI({cpi})가 안정적 수준으로 통화정책 완화 여지가 있습니다.")
        elif cpi >= 4.0:
            score -= 15
            risks.append(f"CPI({cpi})가 높아 긴축 통화정책 지속 가능성이 있습니다.")

    # [영역 3] 경제성장 평가
    # 출처: Miyazaki et al. (2026) — GDP 성장 = 긍정
    # GDP 지표는 이미 전년동기비 값이므로 RoC 계산 생략
    gdp = val("실질 GDP 성장률 (전년동기비)")
    if gdp is not None:
        if gdp >= 2.0:
            score += 10
            reasons.append(f"GDP 성장률({gdp}%)이 양호해 기업 실적 개선 기대가 높습니다.")
        elif gdp <= 0:
            score -= 20
            risks.append(f"GDP 성장률({gdp}%)이 0% 이하로 경기 침체 리스크가 존재합니다.")

    # [영역 4] 시장 심리 평가
    nsi = val("뉴스심리지수")
    if nsi is not None:
        if nsi >= 110:
            score += 5
            reasons.append(f"뉴스심리지수({nsi})가 높아 시장 투자심리가 긍정적입니다.")
        elif nsi <= 90:
            score -= 5
            risks.append(f"뉴스심리지수({nsi})가 낮아 시장 투자심리가 위축되어 있습니다.")

    # [섹터 가중치] 환율 보정
    # 출처: PLOS ONE (2024) — 섹터별 환율 민감도 차별화
    fx = val("원/달러 환율")
    fx_bonus = _SECTOR_FX_BONUS.get(sector, 0)
    if fx is not None and fx >= 1350 and fx_bonus != 0:
        score += fx_bonus
        if fx_bonus > 0:
            reasons.append(f"원화 약세(환율 {fx}원)가 {sector} 수출에 유리하게 작용합니다.")
        else:
            risks.append(f"원화 약세(환율 {fx}원)가 {sector} 업종에 비용 부담으로 작용합니다.")

    # [섹터 가중치] 금리 보정
    rate_bonus = _SECTOR_RATE_BONUS.get(sector, 0)
    if rate is not None and rate_bonus != 0:
        score += rate_bonus
        if rate_bonus > 0:
            reasons.append(f"현 금리 환경({rate}%)이 {sector} 업종에 유리하게 작용합니다.")
        else:
            risks.append(f"현 금리 환경({rate}%)이 {sector} 업종 수익성에 부담을 줍니다.")

    # [RoC 보정] 변화율 추세 반영
    # 출처: Miyazaki et al. (2026) — Level + RoC 동시 분석
    # 데이터 부족 또는 주기 불일치(max_days 초과) 시 자동 생략
    rate_of_change: dict[str, float | None] = {}
    if prev_context and prev_context.get("indicators"):
        prev_indicators = prev_context["indicators"]

        # 금리: 비정기 발표 → max_days=200 (통방위 간격 최대 약 6개월)
        roc_rate = _calc_roc(indicators_raw, prev_indicators, "한국은행 기준금리", max_days=200)
        # CPI: 월별 → max_days=45 (1개월 + 여유)
        roc_cpi  = _calc_roc(indicators_raw, prev_indicators, "소비자물가지수 (CPI)", max_days=45)
        # GDP: 이미 전년동기비 값 → RoC 계산 생략 (성장률의 성장률 방지)
        roc_gdp  = None

        rate_of_change = {
            "기준금리_RoC":  roc_rate,
            "CPI_RoC":       roc_cpi,
            "GDP성장률_RoC": roc_gdp,
        }

        # 금리 하락 추세 → 추가 가점
        if roc_rate is not None and roc_rate < 0:
            score += 5
            reasons.append(f"기준금리가 하락 추세({roc_rate:+.1f}%)로 통화정책 완화 방향입니다.")
        # CPI 상승 추세 → 추가 감점
        if roc_cpi is not None and roc_cpi > 0:
            score -= 3
            risks.append(f"CPI가 상승 추세({roc_cpi:+.1f}%)로 인플레이션 재가속 가능성이 있습니다.")

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
            f"DB 연결 실패로 데모용 거시경제 추정치를 사용했습니다. ({fallback_reason})"
        )
        risks.append(
            "현재 거시경제 결과는 fallback 값이므로 실제 투자 판단 전 DB 연결 후 재확인이 필요합니다."
        )

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