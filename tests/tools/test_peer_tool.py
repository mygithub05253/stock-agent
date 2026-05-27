from stock_agent.tools.peer_tool import (
    CompanyPeer,
    FinancialSnapshot,
    PriceSnapshot,
    calculate_metric_row,
    calculate_relative_position,
    median_or_none,
)


def test_calculate_metric_row_uses_price_and_financial_data() -> None:
    company = CompanyPeer(
        corp_code="00126380",
        stock_code="005930",
        corp_name="삼성전자",
        sector="semiconductor",
    )
    price = PriceSnapshot(
        stock_code="005930",
        base_date="2026-05-25",
        close_price=70000,
        market_cap=420_000_000_000_000,
        volume=10_000_000,
    )
    latest = FinancialSnapshot(
        corp_code="00126380",
        bsns_year=2025,
        revenue=300_000_000_000_000,
        operating_income=30_000_000_000_000,
        net_income=21_000_000_000_000,
        equity=280_000_000_000_000,
        liabilities=70_000_000_000_000,
    )
    previous = FinancialSnapshot(
        corp_code="00126380",
        bsns_year=2024,
        revenue=250_000_000_000_000,
        operating_income=25_000_000_000_000,
        net_income=18_000_000_000_000,
        equity=260_000_000_000_000,
        liabilities=80_000_000_000_000,
    )

    row = calculate_metric_row(company, price, latest, previous)

    assert row.per == 20.0
    assert row.pbr == 1.5
    assert round(row.roe or 0, 4) == 0.075
    assert round(row.revenue_growth or 0, 4) == 0.2
    assert round(row.operating_margin or 0, 4) == 0.1
    assert round(row.debt_ratio or 0, 4) == 0.25
    assert row.data_quality_score == 100
    assert row.metric_flags == []


def test_negative_income_marks_per_not_applicable() -> None:
    company = CompanyPeer(corp_code="00000001", stock_code="000001", corp_name="적자기업", sector="test")
    price = PriceSnapshot(
        stock_code="000001",
        base_date="2026-05-25",
        close_price=1000,
        market_cap=100_000_000_000,
        volume=1000,
    )
    latest = FinancialSnapshot(
        corp_code="00000001",
        bsns_year=2025,
        revenue=10_000_000_000,
        operating_income=-1_000_000_000,
        net_income=-2_000_000_000,
        equity=5_000_000_000,
        liabilities=3_000_000_000,
    )

    row = calculate_metric_row(company, price, latest, None)

    assert row.per is None
    assert "per_not_applicable" in row.metric_flags
    assert "revenue_growth_missing" in row.metric_flags


def test_relative_position_scores_target_against_peers() -> None:
    rows = [
        calculate_metric_row(
            CompanyPeer(corp_code="1", stock_code="AAA001", corp_name="Target", sector="test"),
            PriceSnapshot(stock_code="AAA001", base_date="2026-05-25", close_price=1, market_cap=1000, volume=1),
            FinancialSnapshot(corp_code="1", bsns_year=2025, revenue=100, operating_income=20, net_income=10, equity=100, liabilities=20),
            FinancialSnapshot(corp_code="1", bsns_year=2024, revenue=90, operating_income=18, net_income=9, equity=90, liabilities=20),
        ),
        calculate_metric_row(
            CompanyPeer(corp_code="2", stock_code="BBB001", corp_name="Peer1", sector="test"),
            PriceSnapshot(stock_code="BBB001", base_date="2026-05-25", close_price=1, market_cap=800, volume=1),
            FinancialSnapshot(corp_code="2", bsns_year=2025, revenue=100, operating_income=10, net_income=8, equity=100, liabilities=40),
            FinancialSnapshot(corp_code="2", bsns_year=2024, revenue=95, operating_income=8, net_income=7, equity=90, liabilities=45),
        ),
    ]

    position = calculate_relative_position(rows, "AAA001")

    assert 0 <= position.score <= 100
    assert position.relative_position["roe_percentile"] >= 0.5
    assert position.relative_position["operating_margin_percentile"] >= 0.5


def test_median_or_none_ignores_none_values() -> None:
    assert median_or_none([None, 10.0, 20.0]) == 15.0
    assert median_or_none([None, None]) is None
