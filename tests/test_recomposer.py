from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location(
    "recomposer_module",
    Path(__file__).resolve().parents[1] / "src" / "stock_agent" / "agents" / "recomposer.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
run_recomposer = mod.run_recomposer

from stock_agent.schemas.analysis import (
    AgentState,
    UserProfile,
    Portfolio,
    StrategistResult,
    GuardrailResult,
    QuantResult,
    QualResult,
    CompetitorResult,
)


def test_recomposer_patches_workers():
    user_profile = UserProfile()
    portfolio = Portfolio(holdings=[])
    quant = QuantResult(score=50, valuation_signal="HOLD", metrics={}, reasons=[], risks=[])
    qual = QualResult(score=40, sentiment="neutral", event_types=[], evidence=[], risks=[])
    competitor = CompetitorResult(score=60, peer_summary="", peers=[], evidence=[], warnings=[])
    strategist = StrategistResult(
        signal="HOLD",
        confidence=45,
        suitability=50,
        headline="검토 필요",
        key_reasons=[],
        risks=[],
        next_actions=[],
        degraded=False,
        contributing_agents=[],
        model_provider="test",
        model="mock",
        fallback_used=False,
    )
    guardrail = GuardrailResult(passed=False, warnings=["Insufficient evidence"], revised_headline="", disclaimer="", needs_revision=True, risk_level="medium", checks=[], trace_id=None)

    state = AgentState(
        user_query="테스트",
        user_profile=user_profile,
        portfolio=portfolio,
        strategist=strategist,
        guardrail=guardrail,
        quant=quant,
        qual=qual,
        competitor=competitor,
    )

    new_state = run_recomposer(state)
    assert new_state.quant.reasons
    assert new_state.qual.evidence
    assert new_state.competitor.peer_summary
    assert new_state.strategist.confidence >= 45
