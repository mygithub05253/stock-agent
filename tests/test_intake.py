from stock_agent.intake import (
    build_holding_from_selection,
    build_holding_weights,
    build_portfolio_from_holdings,
)


def test_build_holding_weights_can_use_total_assets_with_cash() -> None:
    holding = build_holding_from_selection("SK하이닉스", qty=1, avg_price=190000)

    weighted = build_holding_weights([holding], total_assets=(holding.market_value or 0) * 2)

    assert weighted[0].weight == 0.5


def test_build_portfolio_from_holdings_weights_include_cash() -> None:
    holding = build_holding_from_selection("SK하이닉스", qty=1, avg_price=190000)
    cash_amount = holding.market_value or 0

    portfolio = build_portfolio_from_holdings([holding], cash_amount=cash_amount)

    assert portfolio.holdings[0].weight == 0.5
    assert portfolio.cash_weight == 0.5


def test_build_portfolio_from_holdings_keeps_empty_portfolio_zero_weighted() -> None:
    portfolio = build_portfolio_from_holdings([], cash_amount=0)

    assert portfolio.holdings == []
    assert portfolio.cash_weight == 0
