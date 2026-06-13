from stock_agent.graph import pipeline
from stock_agent.schemas.analysis import StrategistResult


def test_pipeline_guardrail_redacts_and_downgrades(monkeypatch):
    # fake strategist that outputs PII in headline
    def fake_run_strategist(state):
        state.strategist = StrategistResult(
            signal="BUY",
            confidence=90,
            suitability=90,
            headline="Contact: test@example.com",
            key_reasons=["매출 성장"],
            risks=[],
            next_actions=[],
        )
        return state

    # stub other agent steps to be no-ops
    monkeypatch.setattr(pipeline, "run_strategist", fake_run_strategist)
    monkeypatch.setattr(pipeline, "run_quant", lambda s: s)
    monkeypatch.setattr(pipeline, "run_qual", lambda s: s)
    monkeypatch.setattr(pipeline, "run_competitor", lambda s: s)
    monkeypatch.setattr(pipeline, "run_investment_analyst", lambda s: s)

    out = pipeline.run_phase1_analysis("test query")

    assert out.state.guardrail.passed is False
    assert any("PII" in w for w in out.state.guardrail.warnings)
    assert out.tier1.signal == "HOLD"
    assert "민감 콘텐츠" in out.tier1.headline
