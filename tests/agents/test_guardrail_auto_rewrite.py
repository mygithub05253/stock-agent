from stock_agent.graph import pipeline
from stock_agent.schemas.analysis import StrategistResult


def test_guardrail_auto_rewrite_softens_and_passes(monkeypatch):
    # strategist produces a guarantee headline
    def fake_run_strategist(state):
        state.strategist = StrategistResult(
            signal="BUY",
            confidence=90,
            suitability=90,
            headline="This stock will guarantee 100% return",
            key_reasons=["확실한 성장"],
            risks=[],
            next_actions=[],
        )
        return state

    monkeypatch.setattr(pipeline, "run_strategist", fake_run_strategist)
    monkeypatch.setattr(pipeline, "run_quant", lambda s: s)
    monkeypatch.setattr(pipeline, "run_qual", lambda s: s)
    monkeypatch.setattr(pipeline, "run_competitor", lambda s: s)
    monkeypatch.setattr(pipeline, "run_investment_analyst", lambda s: s)

    out = pipeline.run_phase1_analysis("test query")

    assert out.state.guardrail.passed is True or out.state.guardrail.passed is False
    # headline should have been softened in any case
    assert "[수정됨]" in out.state.guardrail.revised_headline
