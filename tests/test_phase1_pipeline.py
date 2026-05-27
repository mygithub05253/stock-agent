from stock_agent.graph import run_phase1_analysis
from stock_agent.intake import build_portfolio_from_text, parse_holdings_text
from stock_agent.schemas import Holding, Portfolio, UserProfile, UserRequest


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
    assert output.state.user_request is not None
    assert output.state.user_request.intent == "portfolio_review"
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


def test_portfolio_holding_calculates_basic_values() -> None:
    holding = Holding(
        stock_code="005930",
        corp_name="삼성전자",
        sector="반도체",
        avg_price=70000,
        qty=10,
        current_price=77000,
    )
    portfolio = Portfolio(holdings=[holding], cash_weight=0.2)

    assert holding.cost_basis == 700000
    assert holding.market_value == 770000
    assert portfolio.total_market_value == 770000
    assert portfolio.sector_weights() == {"반도체": 1.0}


def test_parse_holdings_text_extracts_supported_stocks() -> None:
    result = parse_holdings_text("삼성전자 10주, SK하이닉스 3주")

    assert not result.warnings
    assert [holding.corp_name for holding in result.holdings] == ["삼성전자", "SK하이닉스"]
    assert [holding.qty for holding in result.holdings] == [10, 3]
    assert round(sum(holding.weight or 0 for holding in result.holdings), 6) == 1


def test_build_portfolio_from_text_returns_warnings_for_unknown_items() -> None:
    portfolio, warnings = build_portfolio_from_text("삼성전자 10주, 모르는종목 5주")

    assert len(portfolio.holdings) == 1
    assert warnings
    assert "모르는종목" in warnings[0]


def test_user_request_keeps_raw_query_with_structured_context() -> None:
    request = UserRequest(
        raw_query="삼성전자 급등했는데 안정형이면 어떻게 할까?",
        intent="holding_review",
        target_stock_code="005930",
        target_corp_name="삼성전자",
        analysis_scope="single_stock",
        urgency_reason="surge",
        requested_depth="summary",
    )

    assert request.raw_query.startswith("삼성전자")
    assert request.intent == "holding_review"
    assert request.urgency_reason == "surge"


def test_phase1_analysis_attaches_user_request() -> None:
    output = run_phase1_analysis("삼성전자 봐줘")

    assert output.state.user_request is not None
    assert output.state.user_request.raw_query == "삼성전자 봐줘"


def test_curator_matches_non_samsung_holding_from_query() -> None:
    output = run_phase1_analysis("SK하이닉스 비중 괜찮아?")

    assert output.state.curator is not None
    assert output.state.curator.stock_code == "000660"
    assert output.state.curator.sector == "반도체"
    assert output.state.user_request is not None
    assert output.state.user_request.target_corp_name == "SK하이닉스"
    assert output.state.user_request.intent == "risk_review"
    assert output.state.user_request.urgency_reason == "general"


def test_curator_classifies_sell_decision_and_urgency() -> None:
    output = run_phase1_analysis("삼성전자 급락했는데 손절해야 해?")

    assert output.state.user_request is not None
    assert output.state.user_request.intent == "sell_decision"
    assert output.state.user_request.urgency_reason == "drop"


def test_curator_classifies_news_urgency() -> None:
    output = run_phase1_analysis("삼성전자 공시 이슈 확인해줘")

    assert output.state.user_request is not None
    assert output.state.user_request.intent == "holding_review"
    assert output.state.user_request.urgency_reason == "news"


def test_strategist_lowers_suitability_for_conservative_high_weight_user() -> None:
    portfolio = Portfolio(
        holdings=[
            Holding(
                stock_code="005930",
                corp_name="삼성전자",
                sector="반도체",
                weight=0.75,
                avg_price=70000,
                qty=20,
                current_price=78000,
            )
        ],
        cash_weight=0.05,
    )
    conservative = UserProfile(
        risk_tolerance="low",
        investment_horizon_months=3,
        max_drawdown_tolerance=-0.05,
        liquidity_need_level="high",
    )
    aggressive = UserProfile(
        risk_tolerance="high",
        investment_horizon_months=24,
        max_drawdown_tolerance=-0.2,
        liquidity_need_level="low",
    )

    conservative_output = run_phase1_analysis(
        "삼성전자 급등했는데 계속 가져가도 돼?",
        user_profile=conservative,
        portfolio=portfolio,
    )
    aggressive_output = run_phase1_analysis(
        "삼성전자 급등했는데 계속 가져가도 돼?",
        user_profile=aggressive,
        portfolio=portfolio,
    )

    assert conservative_output.tier1.suitability < aggressive_output.tier1.suitability
    assert conservative_output.state.user_request is not None
    assert conservative_output.state.user_request.urgency_reason == "surge"
    assert any("리밸런싱" in action for action in conservative_output.state.strategist.next_actions)
    assert any("급등" in action for action in conservative_output.state.strategist.next_actions)
