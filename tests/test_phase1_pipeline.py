from stock_agent.graph import run_phase1_analysis
from stock_agent.schemas import UserProfile


def test_phase1_analysis_returns_guarded_tier1() -> None:
    output = run_phase1_analysis("내 포트폴리오에서 삼성전자 어떻게 할까?")

    assert output.state.curator is not None
    assert output.state.curator.stock_code == "005930"
    assert output.state.quant is not None
    assert output.state.qual is not None
    assert output.state.competitor is not None
    assert output.state.strategist is not None
    assert output.state.guardrail is not None
    assert output.tier1.signal in {"BUY", "HOLD", "SELL"}
    assert "투자 권유" in output.tier1.disclaimer


def test_phase1_analysis_uses_candidates_when_stock_is_missing() -> None:
    output = run_phase1_analysis("요즘 내 포트폴리오에서 볼만한 종목 알려줘")

    assert output.state.curator is not None
    assert output.state.curator.candidates
    assert output.tier1.confidence > 0


def test_user_profile_accepts_phase1_intake_fields() -> None:
    profile = UserProfile(
        risk_tolerance="low",
        investment_horizon_months=24,
        target_return_rate=0.08,
        max_drawdown_tolerance=-0.1,
        investment_goal="wealth_preservation",
        experience_level="beginner",
        preferred_sectors=["반도체", "금융"],
        excluded_sectors=["바이오"],
        liquidity_need_level="high",
    )

    assert profile.risk_tolerance == "low"
    assert profile.target_return_rate == 0.08
    assert profile.max_drawdown_tolerance == -0.1
    assert profile.preferred_sectors == ["반도체", "금융"]
