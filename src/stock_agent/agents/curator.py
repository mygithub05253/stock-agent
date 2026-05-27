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
        request_intent = "portfolio_review"
        if intent == "보유 종목 판단 지원":
            request_intent = "holding_review"
        elif intent == "신규 관심 종목 점검":
            request_intent = "new_recommendation"
        state.user_request = state.user_request.model_copy(
            update={
                "intent": request_intent,
                "target_stock_code": selected["stock_code"],
                "target_corp_name": selected["corp_name"],
                "analysis_scope": "portfolio" if intent == "포트폴리오 전체 점검" else "single_stock",
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
