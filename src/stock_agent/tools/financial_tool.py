import os
import psycopg2
from psycopg2 import OperationalError
from dotenv import load_dotenv

from stock_agent.schemas.analysis import AgentState, QuantResult
from stock_agent.tools.price_tool import get_price_metrics
from stock_agent.tools.financial_tool import get_financial_metrics

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def run_quant(state: AgentState) -> AgentState:
    """
    [Quant Agent] Curator가 확정한 종목에 대해 시세와 재무제표 툴을 호출하여 정량 분석을 수행합니다.
    """
    if state.curator is None:
        raise ValueError("Curator result is required before quant analysis")

    stock_code = state.curator.stock_code
    corp_code = state.curator.corp_code
    
    # 파이프라인에서 as_of_date를 주입하지 않았다면 오늘 날짜를 기본값으로 사용
    as_of_date = getattr(state, "as_of_date", None)
    if not as_of_date:
        from datetime import datetime
        as_of_date = datetime.now().strftime("%Y-%m-%d")

    # DB 커넥션 오픈 및 Tool 호출 (Fallback 예외처리 적용)
    try:
        conn = psycopg2.connect(DATABASE_URL)
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
            price_metrics = get_price_metrics(conn, stock_code, as_of_date)
            fin_metrics = get_financial_metrics(conn, corp_code, as_of_date)
        finally:
            conn.close()
        fallback_reason = None

    # Tool 결과를 통합하여 metrics 생성
    metrics = {
        "per": price_metrics.get("per"),
        "pbr": price_metrics.get("pbr"),
        "roe": fin_metrics.get("roe"),
        "revenue_growth_yoy": fin_metrics.get("revenue_growth_yoy"),
        "operating_margin": fin_metrics.get("operating_margin"),
        "debt_ratio": fin_metrics.get("debt_ratio"),
        "close_price": price_metrics.get("close_price")
    }

    # 💡 [Calculation outside LLM] MVP 룰 기반 점수 및 시그널 산출
    score = 50
    reasons = []
    risks = []
    
    roe = metrics["roe"] or 0
    growth = metrics["revenue_growth_yoy"] or 0
    debt = metrics["debt_ratio"] or 0

    if roe > 10 and growth > 5:
        score += 30
        reasons.append(f"ROE({roe}%)와 매출 성장률({growth}%)이 견조하여 본업 경쟁력이 우수합니다.")
    elif roe <= 0:
        score -= 20
        risks.append("수익성(ROE) 악화로 인해 기초 펀더멘털 리스크가 존재합니다.")
        
    if debt > 150:
        score -= 10
        risks.append(f"부채비율이 {debt}%로 다소 높아 재무 건전성 점검이 필요합니다.")
    else:
        reasons.append("부채비율이 안정적인 수준에서 관리되고 있습니다.")

    if score >= 70:
        valuation_signal = "BUY"
    elif score >= 40:
        valuation_signal = "HOLD"
    else:
        valuation_signal = "SELL"

    if fallback_reason:
        reasons.append(f"DB 연결 실패로 데모용 정량 추정치를 사용했습니다. ({fallback_reason})")
        risks.append("현재 정량 결과는 데모용 fallback 값이므로 실제 투자 판단 전 DB 연결 후 재확인이 필요합니다.")

    # AgentState 갱신
    state.quant = QuantResult(
        score=score,
        valuation_signal=valuation_signal,
        metrics=metrics,
        reasons=reasons if reasons else ["특별한 상승 모멘텀이 식별되지 않았습니다."],
        risks=risks if risks else ["현재 눈에 띄는 정량적 재무 리스크는 없습니다."]
    )
    
    return state