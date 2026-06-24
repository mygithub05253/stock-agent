from stock_agent.graph import pipeline
from stock_agent.schemas.analysis import StrategistResult


def _stub_worker_nodes(monkeypatch):
    monkeypatch.setattr(pipeline, "run_quant", lambda s: s)
    monkeypatch.setattr(pipeline, "run_qual", lambda s: s)
    monkeypatch.setattr(pipeline, "run_competitor", lambda s: s)
    monkeypatch.setattr(pipeline, "run_macro", lambda s: s)
    monkeypatch.setattr(pipeline, "run_investment_analyst", lambda s: s)


def test_pipeline_guardrail_redacts_and_downgrades(monkeypatch):
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

    monkeypatch.setattr(pipeline, "run_strategist", fake_run_strategist)
    _stub_worker_nodes(monkeypatch)

    out = pipeline.run_phase1_analysis("test query")

    assert out.state.guardrail.passed is False
    assert any("PII" in w for w in out.state.guardrail.warnings)
    assert out.tier1.signal == "HOLD"
    assert "민감 콘텐츠" in out.tier1.headline


def test_pipeline_guardrail_retries_revisable_failure(monkeypatch):
    calls = {"strategist": 0}

    def fake_run_strategist(state):
        calls["strategist"] += 1
        if calls["strategist"] == 1:
            state.strategist = StrategistResult(
                signal="BUY",
                confidence=80,
                suitability=80,
                headline="근거가 부족한 매수 의견입니다.",
                key_reasons=["단일 근거"],
                risks=[],
                next_actions=[],
            )
        else:
            state.strategist = StrategistResult(
                signal="HOLD",
                confidence=65,
                suitability=60,
                headline="추가 근거를 반영해 보유 유지 검토가 우세합니다.",
                key_reasons=["정량 근거 보강", "정성 근거 보강"],
                risks=["추가 확인 필요"],
                next_actions=["실적과 업황 지표를 재확인합니다."],
            )
        return state

    monkeypatch.setattr(pipeline, "run_strategist", fake_run_strategist)
    _stub_worker_nodes(monkeypatch)

    out = pipeline.run_phase1_analysis("test query")

    assert calls["strategist"] >= 2
    assert out.state.guardrail.passed is True
    assert out.state.guardrail.needs_revision is False
    assert out.tier1.headline == "추가 근거를 반영해 보유 유지 검토가 우세합니다."


def test_pipeline_guardrail_revision_strategy_failure_is_degraded(monkeypatch):
    calls = {"strategist": 0}

    def fake_run_strategist(state):
        calls["strategist"] += 1
        if calls["strategist"] > 1:
            raise RuntimeError("revision strategist unavailable")
        state.strategist = StrategistResult(
            signal="BUY",
            confidence=80,
            suitability=80,
            headline="근거가 부족한 매수 의견입니다.",
            key_reasons=["단일 근거"],
            risks=[],
            next_actions=[],
        )
        return state

    monkeypatch.setattr(pipeline, "run_strategist", fake_run_strategist)
    _stub_worker_nodes(monkeypatch)

    out = pipeline.run_phase1_analysis("test query")

    assert calls["strategist"] == 2
    assert out.state.strategist.degraded is True
    assert out.state.strategist.fallback_used is True
    assert any("recomposition_strategy_failed" in err for err in out.state.worker_errors)
    assert out.state.guardrail.needs_revision is True
