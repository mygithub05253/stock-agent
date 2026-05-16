from stock_agent.schemas.analysis import AgentState, GuardrailResult


_BANNED_PHRASES = {
    "무조건 매수": "매수 우위의 분석 신호",
    "무조건 매도": "매도 우위의 분석 신호",
    "수익 보장": "수익 가능성",
    "확실한 수익": "기대 수익",
}


def run_guardrail(state: AgentState) -> AgentState:
    if state.strategist is None:
        raise ValueError("strategist result is required before guardrail")

    headline = state.strategist.headline
    warnings: list[str] = []
    for banned, replacement in _BANNED_PHRASES.items():
        if banned in headline:
            headline = headline.replace(banned, replacement)
            warnings.append(f"투자 권유성 표현을 완화했습니다: {banned}")

    if state.qual is not None and any("mock" in risk.lower() for risk in state.qual.risks):
        warnings.append("뉴스/공시 근거는 mock 데이터이므로 실제 RAG 연결 전까지 신뢰도를 보수적으로 표시합니다.")

    state.guardrail = GuardrailResult(
        passed=True,
        warnings=warnings,
        revised_headline=headline,
        disclaimer="본 결과는 투자 권유가 아니라 데이터 기반 분석 신호입니다. 최종 투자 판단과 책임은 사용자에게 있습니다.",
    )
    return state
