from stock_agent.schemas.analysis import AgentState


def _detect_urgency_reason(query: str) -> str:
    if any(keyword in query for keyword in ("급등", "상승", "올랐")):
        return "surge"
    if any(keyword in query for keyword in ("급락", "하락", "떨어졌", "빠졌")):
        return "drop"
    if any(keyword in query for keyword in ("실적", "어닝", "발표")):
        return "earnings"
    if any(keyword in query for keyword in ("뉴스", "공시", "이슈")):
        return "news"
    return "general"


def _classify_request_intent(query: str, curator_intent: str) -> str:
    if curator_intent == "포트폴리오 전체 점검":
        return "portfolio_review"
    if any(keyword in query for keyword in ("팔", "매도", "익절", "손절", "정리")):
        return "sell_decision"
    if any(keyword in query for keyword in ("위험", "리스크", "괜찮", "비중", "손실")):
        return "risk_review"
    if curator_intent == "신규 관심 종목 점검":
        return "new_recommendation"
    return "holding_review"


def run_request_classifier(state: AgentState) -> AgentState:
    if state.user_request is None:
        return state
    if state.curator is None:
        raise ValueError("curator result is required before request classification")

    query = state.user_request.raw_query.lower()
    state.user_request = state.user_request.model_copy(
        update={
            "intent": _classify_request_intent(query, state.curator.intent),
            "target_stock_code": state.curator.stock_code,
            "target_corp_name": state.curator.corp_name,
            "analysis_scope": (
                "portfolio" if state.curator.intent == "포트폴리오 전체 점검" else "single_stock"
            ),
            "urgency_reason": _detect_urgency_reason(query),
        }
    )
    return state
