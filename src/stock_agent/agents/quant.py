import time

import psycopg2

from stock_agent.agents.fallback import ensure_database_available
from stock_agent.config import get_settings
from stock_agent.schemas.analysis import AgentState, QuantResult
from stock_agent.tools.financial_tool import get_financial_metrics
from stock_agent.tools.price_tool import get_price_metrics

_RETRYABLE_DB_CONNECT_ATTEMPTS = 3
_DB_CONNECT_BACKOFF_SECONDS = (0.5, 1.0)

_DEFAULT_PRICE_METRICS = {
    "per": 18.0,
    "pbr": 1.3,
    "close_price": 0,
}
_DEFAULT_FIN_METRICS = {
    "roe": 8.0,
    "revenue_growth_yoy": 4.0,
    "operating_margin": 12.0,
    "debt_ratio": 90.0,
}


def _connect_with_retry() -> tuple[object | None, list[str]]:
    settings = get_settings()
    reasons: list[str] = []

    for attempt in range(1, _RETRYABLE_DB_CONNECT_ATTEMPTS + 1):
        try:
            return psycopg2.connect(settings.resolved_database_url), reasons
        except Exception as exc:
            reasons.append(
                f"DB 연결 시도 {attempt} 실패: {exc.__class__.__name__}: {exc}"
            )
            if attempt < _RETRYABLE_DB_CONNECT_ATTEMPTS:
                time.sleep(
                    _DB_CONNECT_BACKOFF_SECONDS[
                        min(attempt - 1, len(_DB_CONNECT_BACKOFF_SECONDS) - 1)
                    ]
                )

    return None, reasons


def _normalize_metrics(raw: dict[str, float | int], fallback: dict[str, float | int]) -> dict[str, float | int]:
    return {
        key: float(raw.get(key)) if raw.get(key) is not None else fallback[key]
        for key in fallback
    }

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL") or get_settings().resolved_database_url

def run_quant(state: AgentState) -> AgentState:
    """
    [Quant Agent] Curator가 확정한 종목에 대해 시세와 재무제표 툴을 호출하여 정량 분석을 수행합니다.
    """
    if state.curator is None:
        raise ValueError("Curator result is required before quant analysis")

    stock_code = state.curator.stock_code
    corp_code = state.curator.corp_code

    as_of_date = getattr(state, "as_of_date", None)
    if not as_of_date:
        from datetime import datetime

        as_of_date = datetime.now().strftime("%Y-%m-%d")

    price_metrics: dict[str, float | int] = _DEFAULT_PRICE_METRICS.copy()
    fin_metrics: dict[str, float | int] = _DEFAULT_FIN_METRICS.copy()
    price_source = "fallback"
    fin_source = "fallback"
    fallback_reasons: list[str] = []

    conn, connect_reasons = _connect_with_retry()
    if conn is None:
        fallback_reasons.extend(connect_reasons)
        
    # DB 커넥션 오픈 및 Tool 호출
    try:
        ensure_database_available()
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=1)
    except (OperationalError, Exception) as exc:
        price_metrics = {
            "per": 18.0,
            "pbr": 1.3,
            "close_price": 0,
        }
        fin_metrics = {
            "roe": 8.0,
            "revenue_growth_yoy": 4.0,
            "operating_margin": 12.0,
            "debt_ratio": 90.0,
        }
        fallback_reason = f"{exc.__class__.__name__}: {exc}"

    else:
        try:
            try:
                price_metrics = get_price_metrics(conn, stock_code, as_of_date)
                price_source = "db"
            except Exception as exc:
                fallback_reasons.append(
                    f"시세 도구 오류: {exc.__class__.__name__}: {exc}"
                )
                price_metrics = _DEFAULT_PRICE_METRICS.copy()

            try:
                fin_metrics = get_financial_metrics(conn, corp_code, as_of_date)
                fin_source = "db"
            except Exception as exc:
                fallback_reasons.append(
                    f"DART 재무 도구 오류: {exc.__class__.__name__}: {exc}"
                )
                fin_metrics = _DEFAULT_FIN_METRICS.copy()
        finally:
            try:
                conn.close()
            except Exception:
                pass

    price_metrics = _normalize_metrics(price_metrics, _DEFAULT_PRICE_METRICS)
    fin_metrics = _normalize_metrics(fin_metrics, _DEFAULT_FIN_METRICS)

    metrics = {
        "per": price_metrics.get("per"),
        "pbr": price_metrics.get("pbr"),
        "roe": fin_metrics.get("roe"),
        "revenue_growth_yoy": fin_metrics.get("revenue_growth_yoy"),
        "operating_margin": fin_metrics.get("operating_margin"),
        "debt_ratio": fin_metrics.get("debt_ratio"),
        "close_price": price_metrics.get("close_price"),
    }

    score = 50
    reasons: list[str] = []
    risks: list[str] = []

    roe = metrics["roe"] or 0
    growth = metrics["revenue_growth_yoy"] or 0
    debt = metrics["debt_ratio"] or 0

    if roe > 10 and growth > 5:
        score += 30
        reasons.append(
            f"ROE({roe}%)와 매출 성장률({growth}%)이 견조하여 본업 경쟁력이 우수합니다."
        )
    elif roe <= 0:
        score -= 20
        risks.append(
            "수익성(ROE) 악화로 인해 기초 펀더멘털 리스크가 존재합니다."
        )

    if debt > 150:
        score -= 10
        risks.append(
            f"부채비율이 {debt}%로 다소 높아 재무 건전성 점검이 필요합니다."
        )
    else:
        reasons.append("부채비율이 안정적인 수준에서 관리되고 있습니다.")

    if price_source == "db":
        reasons.append(
            f"{as_of_date} 기준 {stock_code}의 시세와 밸류에이션 지표를 DB에서 조회했습니다."
        )
    else:
        reasons.append(
            "시세 데이터 조회가 불완전하여 데모용 fallback 값이 사용되었습니다."
        )

    if fin_source == "db":
        reasons.append(
            f"{as_of_date} 기준 {corp_code}의 DART 재무 지표를 DB에서 조회했습니다."
        )
    else:
        reasons.append(
            "재무 지표 조회가 불완전하여 데모용 fallback 값이 사용되었습니다."
        )

    if fallback_reasons:
        reasons.append(
            "일부 정량 지표는 데모 또는 기본값으로 대체되어 있습니다. 실제 투자 판단 전 DB/툴 연결 결과를 재확인하세요."
        )
        risks.append(
            "현재 정량 결과에는 일부 mock/기본값이 포함되어 있으므로 검증이 필요합니다."
        )
        for fallback_reason in fallback_reasons:
            reasons.append(fallback_reason)

    if score >= 70:
        valuation_signal = "BUY"
    elif score >= 40:
        valuation_signal = "HOLD"
    else:
        valuation_signal = "SELL"

    state.quant = QuantResult(
        score=score,
        valuation_signal=valuation_signal,
        metrics=metrics,
        reasons=reasons if reasons else ["특별한 상승 모멘텀이 식별되지 않았습니다."],
        risks=risks if risks else ["현재 눈에 띄는 정량적 재무 리스크는 없습니다."]
    )
    
    return state
