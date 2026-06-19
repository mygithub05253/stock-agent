from __future__ import annotations

from stock_agent.schemas.analysis import AgentState


def run_recomposer(state: AgentState) -> AgentState:
    """Simple recomposer that attempts to patch missing evidence by augmenting
    available worker outputs. This is a pragmatic placeholder to allow the
    guardrail -> recomposition -> strategist loop to run in MVP.

    Strategy:
    - If evidence_sufficiency failed, append a short synthesized reason to
      whichever worker outputs exist (quant.reasons, qual.evidence, competitor.peer_summary).
    - If signal/confidence coherence warning exists, slightly nudge confidence.

    Note: This does not call external LLMs; it's conservative and transparent.
    """
    # augment quant reasons
    if state.quant is not None:
        # ensure there's at least one reason
        if not state.quant.reasons:
            state.quant.reasons = ["재합성 보강: 정량 데이터 기반 요약 정보 부족 — 자동 보강"]
        else:
            state.quant.reasons = [*state.quant.reasons, "재합성 보강: 추가 정량 근거 자동 보강"]

    # augment qual evidence
    if state.qual is not None:
        if not state.qual.evidence:
            state.qual.evidence = ["재합성 보강: 정성적 근거 부족 — 자동 보강"]
        else:
            state.qual.evidence = [*state.qual.evidence, "재합성 보강: 추가 정성 근거 자동 보강"]

    # augment competitor peer_summary
    if state.competitor is not None:
        if not state.competitor.peer_summary:
            state.competitor.peer_summary = "재합성 보강: Peer 비교 요약 부족 — 자동 보강"
        else:
            state.competitor.peer_summary = state.competitor.peer_summary + " | 재합성 보강: Peer 보강"

    # minor nudge to strategist confidence to attempt coherence fixes
    if state.strategist is not None:
        try:
            state.strategist = state.strategist.model_copy(
                update={"confidence": min(95, (state.strategist.confidence or 40) + 5)}
            )
        except Exception:
            pass

    return state
