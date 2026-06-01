from stock_agent.tools import peer_tool
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


def test_relative_position_returns_zero_when_no_comparable_peers() -> None:
    target = calculate_metric_row(
        CompanyPeer(corp_code="1", stock_code="AAA001", corp_name="Target", sector="test"),
        PriceSnapshot(stock_code="AAA001", base_date="2026-05-25", close_price=1, market_cap=1000, volume=1),
        FinancialSnapshot(
            corp_code="1",
            bsns_year=2025,
            revenue=100,
            operating_income=20,
            net_income=10,
            equity=100,
            liabilities=20,
        ),
        FinancialSnapshot(
            corp_code="1",
            bsns_year=2024,
            revenue=90,
            operating_income=18,
            net_income=9,
            equity=90,
            liabilities=20,
        ),
    )

    position = calculate_relative_position([target], "AAA001")

    assert position.score == 0
    assert position.relative_position["valuation_percentile"] is None
    assert position.relative_position["data_quality_score"] == 100
    assert "no_comparable_peers" in position.data_quality_flags
    assert "peer_count_below_minimum" in position.data_quality_flags
    assert position.a1_peer_multiple_payload == {"median_per": None, "median_pbr": None}


def test_median_or_none_ignores_none_values() -> None:
    assert median_or_none([None, 10.0, 20.0]) == 15.0
    assert median_or_none([None, None]) is None


def test_select_peer_rows_excludes_target_and_prefers_quality_then_market_cap_proximity() -> None:
    target = peer_tool.PeerMetricRow(
        corp_code="1",
        stock_code="AAA001",
        corp_name="Target",
        sector="semiconductor",
        market_cap=1_000,
        data_quality_score=100,
    )
    low_quality_close_peer = peer_tool.PeerMetricRow(
        corp_code="2",
        stock_code="BBB001",
        corp_name="Lower Quality Close",
        sector="semiconductor",
        market_cap=1_010,
        data_quality_score=60,
    )
    high_quality_far_peer = peer_tool.PeerMetricRow(
        corp_code="3",
        stock_code="CCC001",
        corp_name="High Quality Far",
        sector="semiconductor",

        market_cap=3_500,  # 3.5x — within 0.25x~4x band
        data_quality_score=90,
    )
    high_quality_close_peer = peer_tool.PeerMetricRow(
        corp_code="4",
        stock_code="DDD001",
        corp_name="High Quality Close",
        sector="semiconductor",
        market_cap=1_050,
        data_quality_score=90,
    )

    selected = peer_tool.select_peer_rows(
        target,
        [target, low_quality_close_peer, high_quality_far_peer, high_quality_close_peer],
        max_peer_count=2,
    )

    assert [row.stock_code for row in selected] == ["DDD001", "CCC001"]


def test_load_peer_candidates_fetches_broader_candidate_pool(monkeypatch) -> None:
    target = CompanyPeer(corp_code="1", stock_code="AAA001", corp_name="Target", sector="semiconductor")
    captured_params = None

    def fake_fetch_all(conn, query, params):
        nonlocal captured_params
        captured_params = params
        return [
            {
                "corp_code": "2",
                "stock_code": "BBB001",
                "corp_name": "Peer B",
                "sector": "semiconductor",
            }
        ]

    monkeypatch.setattr(peer_tool, "_fetch_all", fake_fetch_all)

    peers = peer_tool.load_peer_candidates(object(), target, max_peer_count=3)

    assert [peer.stock_code for peer in peers] == ["BBB001"]
    assert captured_params == ("semiconductor", "AAA001", 20)


def test_build_peer_summary_mentions_peer_count_and_warnings() -> None:
    target = peer_tool.PeerMetricRow(
        corp_code="1",
        stock_code="AAA001",
        corp_name="Target",
        sector="semiconductor",
        data_quality_score=100,
    )

    summary = peer_tool.build_peer_summary(
        target,
        peer_count=2,
        data_quality_flags=["peer_count_below_minimum", "sector_missing", "target_data_quality_low"],
    )

    assert "2개" in summary
    assert "비교 가능한 peer 수가 부족해 결과 해석이 제한적입니다." in summary
    assert "섹터 정보가 없어 자동 peer 선정이 제한되었습니다." in summary
    assert "대상 종목의 핵심 지표가 부족해 점수를 보수적으로 해석해야 합니다." in summary
    assert "peer_count_below_minimum" not in summary
    assert "sector_missing" not in summary
    assert "target_data_quality_low" not in summary


def test_build_peer_comparison_orchestrates_loaders_and_returns_position(monkeypatch) -> None:
    target = CompanyPeer(corp_code="1", stock_code="AAA001", corp_name="Target", sector=None)
    peers = [
        CompanyPeer(corp_code="2", stock_code="BBB001", corp_name="Peer B", sector="semiconductor"),
        CompanyPeer(corp_code="3", stock_code="CCC001", corp_name="Peer C", sector="semiconductor"),
        CompanyPeer(corp_code="4", stock_code="DDD001", corp_name="Peer D", sector="semiconductor"),
    ]

    def fake_load_target_company(conn, stock_code):
        assert stock_code == "AAA001"
        return target

    def fake_load_peer_candidates(conn, target_company, max_peer_count=8):
        assert target_company.sector == "semiconductor"
        return peers

    def fake_load_latest_prices(conn, stock_codes):
        assert stock_codes == ["AAA001", "BBB001", "CCC001", "DDD001"]
        return {
            "AAA001": PriceSnapshot(
                stock_code="AAA001",
                base_date="2026-05-25",
                close_price=100,
                market_cap=1_000,
                volume=10,
            ),
            "BBB001": PriceSnapshot(
                stock_code="BBB001",
                base_date="2026-05-25",
                close_price=100,
                market_cap=1_050,
                volume=10,
            ),
            "CCC001": PriceSnapshot(
                stock_code="CCC001",
                base_date="2026-05-25",
                close_price=100,
                market_cap=1_100,
                volume=10,
            ),
            "DDD001": PriceSnapshot(
                stock_code="DDD001",
                base_date="2026-05-25",
                close_price=100,
                market_cap=5_000,
                volume=10,
            ),
        }

    def fake_load_financial_snapshots(conn, corp_codes, lookback_years=3):
        assert corp_codes == ["1", "2", "3", "4"]
        assert lookback_years == 3
        return {
            corp_code: (
                FinancialSnapshot(
                    corp_code=corp_code,
                    bsns_year=2025,
                    revenue=100,
                    operating_income=20,
                    net_income=10,
                    equity=100,
                    liabilities=20,
                ),
                FinancialSnapshot(
                    corp_code=corp_code,
                    bsns_year=2024,
                    revenue=90,
                    operating_income=18,
                    net_income=9,
                    equity=90,
                    liabilities=20,
                ),
            )
            for corp_code in ["1", "2", "3", "4"]
        }

    monkeypatch.setattr(peer_tool, "load_target_company", fake_load_target_company)
    monkeypatch.setattr(peer_tool, "load_peer_candidates", fake_load_peer_candidates)
    monkeypatch.setattr(peer_tool, "load_latest_prices", fake_load_latest_prices)
    monkeypatch.setattr(peer_tool, "load_financial_snapshots", fake_load_financial_snapshots)

    comparison = peer_tool.build_peer_comparison(
        object(),
        "AAA001",
        sector="semiconductor",
        min_peer_count=3,
        max_peer_count=2,
    )

    assert comparison.score > 0
    assert [row.stock_code for row in comparison.peers] == ["BBB001", "CCC001"]
    assert "peer_count_below_minimum" in comparison.warnings
    assert comparison.evidence
    assert comparison.a1_peer_multiple_payload == {"median_per": 107.5, "median_pbr": 10.75}


def test_build_peer_comparison_limits_score_when_no_peers(monkeypatch) -> None:
    target = CompanyPeer(corp_code="1", stock_code="AAA001", corp_name="Target", sector=None)

    def fake_load_target_company(conn, stock_code):
        assert stock_code == "AAA001"
        return target

    def fake_load_latest_prices(conn, stock_codes):
        assert stock_codes == ["AAA001"]
        return {
            "AAA001": PriceSnapshot(
                stock_code="AAA001",
                base_date="2026-05-25",
                close_price=100,
                market_cap=1_000,
                volume=10,
            )
        }

    def fake_load_financial_snapshots(conn, corp_codes, lookback_years=3):
        assert corp_codes == ["1"]
        return {
            "1": (
                FinancialSnapshot(
                    corp_code="1",
                    bsns_year=2025,
                    revenue=100,
                    operating_income=20,
                    net_income=10,
                    equity=100,
                    liabilities=20,
                ),
                FinancialSnapshot(
                    corp_code="1",
                    bsns_year=2024,
                    revenue=90,
                    operating_income=18,
                    net_income=9,
                    equity=90,
                    liabilities=20,
                ),
            )
        }

    monkeypatch.setattr(peer_tool, "load_target_company", fake_load_target_company)
    monkeypatch.setattr(peer_tool, "load_latest_prices", fake_load_latest_prices)
    monkeypatch.setattr(peer_tool, "load_financial_snapshots", fake_load_financial_snapshots)

    comparison = peer_tool.build_peer_comparison(object(), "AAA001")

    assert comparison.score == 0
    assert comparison.peers == []
    assert "sector_missing" in comparison.warnings
    assert "peer_count_below_minimum" in comparison.warnings
    assert "no_comparable_peers" in comparison.data_quality_flags



def test_select_peer_rows_filters_by_market_cap_band() -> None:
    from stock_agent.tools.peer_tool import PeerMetricRow, select_peer_rows

    target = PeerMetricRow(
        corp_code="T", stock_code="TGT001", corp_name="Target",
        sector="test", market_cap=1_000_000, data_quality_score=100,
    )
    within_band = PeerMetricRow(
        corp_code="A", stock_code="AAA001", corp_name="WithinBand",
        sector="test", market_cap=500_000,
        data_quality_score=100,
    )
    outside_band = PeerMetricRow(
        corp_code="B", stock_code="BBB001", corp_name="OutsideBand",
        sector="test", market_cap=10_000,
        data_quality_score=100,
    )
    no_market_cap = PeerMetricRow(
        corp_code="C", stock_code="CCC001", corp_name="NoMarketCap",
        sector="test", market_cap=None, data_quality_score=90,
    )

    rows = [target, within_band, outside_band, no_market_cap]
    selected = select_peer_rows(target, rows, max_peer_count=10)

    stock_codes = [r.stock_code for r in selected]
    assert "AAA001" in stock_codes
    assert "BBB001" not in stock_codes
    assert "CCC001" in stock_codes


def test_select_peer_rows_keeps_all_when_target_has_no_market_cap() -> None:
    from stock_agent.tools.peer_tool import PeerMetricRow, select_peer_rows

    target = PeerMetricRow(
        corp_code="T", stock_code="TGT001", corp_name="Target",
        sector="test", market_cap=None, data_quality_score=100,
    )
    peer_a = PeerMetricRow(
        corp_code="A", stock_code="AAA001", corp_name="PeerA",
        sector="test", market_cap=999, data_quality_score=100,
    )
    peer_b = PeerMetricRow(
        corp_code="B", stock_code="BBB001", corp_name="PeerB",
        sector="test", market_cap=1, data_quality_score=80,
    )

    selected = select_peer_rows(target, [target, peer_a, peer_b], max_peer_count=10)
    assert len(selected) == 2


def test_mark_outliers_flags_extreme_values() -> None:
    from stock_agent.tools.peer_tool import PeerMetricRow, _mark_outliers

    target = PeerMetricRow(
        corp_code="T", stock_code="TGT001", corp_name="Target",
        sector="test", data_quality_score=100, per=200.0,
    )
    peer_a = PeerMetricRow(
        corp_code="A", stock_code="AAA001", corp_name="PeerA",
        sector="test", data_quality_score=100, per=18.0,
    )
    peer_b = PeerMetricRow(
        corp_code="B", stock_code="BBB001", corp_name="PeerB",
        sector="test", data_quality_score=100, per=20.0,
    )

    result = _mark_outliers([target, peer_a, peer_b], "TGT001")
    target_row = next(r for r in result if r.stock_code == "TGT001")
    assert "outlier_per" in target_row.metric_flags
