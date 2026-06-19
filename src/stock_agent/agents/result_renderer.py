from __future__ import annotations

from stock_agent.schemas.analysis import AgentState, RenderedReport


def run_result_renderer(state: AgentState) -> AgentState:
    """Convert strategist+guardrail results into a user-facing RenderedReport."""
    strategist = state.strategist
    guardrail = state.guardrail

    if strategist is None:
        raise ValueError("strategist result is required before rendering")

    # Use revised headline from guardrail when available, fall back to strategist headline
    summary = (guardrail.revised_headline if guardrail and guardrail.revised_headline else strategist.headline)

    recommendation_map = {
        "BUY": "매수 검토",
        "HOLD": "보유 유지",
        "SELL": "비중 축소 검토",
    }

    recommendation = recommendation_map.get(strategist.signal, "보류")

    strengths = strategist.key_reasons or []
    risks = strategist.risks or []
    actions = strategist.next_actions or []

    state.rendered_report = RenderedReport(
        summary=summary,
        recommendation=recommendation,
        strengths=strengths,
        risks=risks,
        actions=actions,
    )
    return state
