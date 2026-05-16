from stock_agent.schemas.analysis import AgentState, CuratorResult


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
}


def run_curator(state: AgentState) -> AgentState:
    query = state.user_query.lower()
    selected = None
    for alias, company in _COMPANY_ALIASES.items():
        if alias.lower() in query:
            selected = company
            break

    if selected is None:
        selected = _COMPANY_ALIASES["삼성전자"]
        candidates = ["삼성전자", "SK하이닉스", "현대차", "NAVER", "LG에너지솔루션"]
        intent = "종목 미지정 포트폴리오 점검"
    else:
        candidates = []
        intent = "보유 종목 판단 지원"

    state.curator = CuratorResult(
        intent=intent,
        corp_name=selected["corp_name"],
        stock_code=selected["stock_code"],
        corp_code=selected["corp_code"],
        sector=selected["sector"],
        candidates=candidates,
    )
    return state
