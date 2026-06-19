from stock_agent.schemas.analysis import (
    AgentState,
    UserProfile,
    Portfolio,
    StrategistResult,
    GuardrailResult,
)
import importlib.util
from pathlib import Path

# load module without importing package-level agents __init__ to avoid heavy imports
spec = importlib.util.spec_from_file_location(
    "test_result_renderer_module",
    Path(__file__).resolve().parents[1] / "src" / "stock_agent" / "agents" / "result_renderer.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
run_result_renderer = mod.run_result_renderer


def test_result_renderer_basic():
    user_profile = UserProfile()
    portfolio = Portfolio(holdings=[])
    strategist = StrategistResult(
        signal="BUY",
        confidence=82,
        suitability=74,
        headline="성장 기대",
        key_reasons=["PER 저평가", "HBM 수요 증가", "경쟁사 대비 우위"],
        risks=["중국 수요 둔화", "메모리 가격 변동성"],
        next_actions=["목표가 설정", "모니터링"],
        degraded=False,
        contributing_agents=["quant", "qual", "competitor"],
        model_provider="test",
        model="mock",
        fallback_used=False,
    )
    guardrail = GuardrailResult(
        passed=True,
        warnings=[],
        revised_headline="",
        disclaimer="",
        needs_revision=False,
        risk_level="low",
        checks=[],
        trace_id=None,
    )

    state = AgentState(
        user_query="테스트",
        user_profile=user_profile,
        portfolio=portfolio,
        strategist=strategist,
        guardrail=guardrail,
    )

    new_state = run_result_renderer(state)
    assert new_state.rendered_report is not None
    assert "PER" in new_state.rendered_report.strengths[0]
    assert new_state.rendered_report.recommendation in ("매수 검토", "보류")
