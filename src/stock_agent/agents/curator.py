from stock_agent.schemas.analysis import AgentState, CuratorResult


_MVP_SECTORS = {"반도체", "금융"}
_COMPANY_ALIASES = {
    "삼성전자": {
        "corp_name": "삼성전자",
        "stock_code": "005930",
        "corp_code": "00126380",
        "sector": "반도체",
    },
    "samsung": {
        "corp_name": "삼성전자",
        "stock_code": "005930",
        "corp_code": "00126380",
        "sector": "반도체",
    },
    "sk하이닉스": {
        "corp_name": "SK하이닉스",
        "stock_code": "000660",
        "corp_code": None,
        "sector": "반도체",
    },
    "하이닉스": {
        "corp_name": "SK하이닉스",
        "stock_code": "000660",
        "corp_code": None,
        "sector": "반도체",
    },
    "kb금융": {
        "corp_name": "KB금융",
        "stock_code": "105560",
        "corp_code": None,
        "sector": "금융",
    },
    "신한지주": {
        "corp_name": "신한지주",
        "stock_code": "055550",
        "corp_code": None,
        "sector": "금융",
    },
}


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


def run_curator(state: AgentState) -> AgentState:
    query = (state.user_request.raw_query if state.user_request else state.user_query).lower()
    selected = None
    for alias, company in _COMPANY_ALIASES.items():
        if alias.lower() in query or company["stock_code"] in query:
            selected = company
            break

    holding_by_code = {holding.stock_code: holding for holding in state.portfolio.holdings}
    holding_by_name = {holding.corp_name.lower(): holding for holding in state.portfolio.holdings}
    if selected is None:
        for corp_name, holding in holding_by_name.items():
            if corp_name in query or holding.stock_code in query:
                selected = {
                    "corp_name": holding.corp_name,
                    "stock_code": holding.stock_code,
                    "corp_code": None,
                    "sector": holding.sector or "미분류",
                }
                break

    warnings: list[str] = []
    if selected is None:
        preferred_sectors = set(state.user_profile.preferred_sectors)
        candidate_holdings = [
            holding
            for holding in state.portfolio.holdings
            if not preferred_sectors or holding.sector in preferred_sectors
        ]
        if not candidate_holdings:
            candidate_holdings = state.portfolio.holdings

        selected_holding = candidate_holdings[0] if candidate_holdings else None
        if selected_holding is None:
            selected = _COMPANY_ALIASES["삼성전자"]
            candidates = ["삼성전자", "SK하이닉스", "KB금융", "신한지주"]
            warnings.append("보유 종목이 없어 MVP 기본 후보를 반환했습니다.")
        else:
            selected = {
                "corp_name": selected_holding.corp_name,
                "stock_code": selected_holding.stock_code,
                "corp_code": None,
                "sector": selected_holding.sector or "미분류",
            }
            candidates = [holding.corp_name for holding in candidate_holdings]
        intent = "포트폴리오 전체 점검"
    else:
        candidates = []
        is_holding = selected["stock_code"] in holding_by_code
        intent = "보유 종목 판단 지원" if is_holding else "신규 관심 종목 점검"

    if selected["sector"] not in _MVP_SECTORS:
        warnings.append(f"MVP 지원 산업은 반도체/금융 중심입니다: {selected['sector']}")

    if state.user_request is not None:
        request_intent = _classify_request_intent(query, intent)
        state.user_request = state.user_request.model_copy(
            update={
                "intent": request_intent,
                "target_stock_code": selected["stock_code"],
                "target_corp_name": selected["corp_name"],
                "analysis_scope": "portfolio" if intent == "포트폴리오 전체 점검" else "single_stock",
                "urgency_reason": _detect_urgency_reason(query),
            }
        )

    state.curator = CuratorResult(
        intent=intent,
        corp_name=selected["corp_name"],
        stock_code=selected["stock_code"],
        corp_code=selected["corp_code"],
        sector=selected["sector"],
        candidates=candidates,
        warnings=warnings,
    )
    return state
