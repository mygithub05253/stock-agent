from types import SimpleNamespace

import pytest

from stock_agent.agents import competitor as competitor_module
from stock_agent.schemas.analysis import AgentState, CuratorResult, Portfolio, UserProfile
from stock_agent.tools.peer_tool import PeerComparison, PeerMetricRow


def _stub_settings(**overrides):
    base = dict(
        openrouter_api_key=None,
        competitor_mcp_fallback_enabled=False,
        competitor_mcp_timeout_seconds=20.0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def no_openrouter_key(monkeypatch):
    """로컬 .env에 OpenRouter 키가 있어도 테스트가 실제 LLM을 호출(과금)하지 않도록 차단한다.

    기본값으로 MCP 폴백을 끈다(실서버·네트워크 미사용). MCP 경로 테스트는 개별적으로 켠다.
    """
    monkeypatch.setattr(competitor_module, "get_settings", _stub_settings)


def _state_with_curator() -> AgentState:
    return AgentState(
        user_query="삼성전자 경쟁사와 비교해줘",
        user_profile=UserProfile(),
        portfolio=Portfolio(),
        curator=CuratorResult(
            intent="stock_analysis",
            corp_name="Target Co",
            stock_code="AAA001",
            corp_code="1",
            sector="semiconductor",
        ),
    )


def test_run_competitor_uses_peer_tool_result(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeConnection:
        def __enter__(self):
            captured["entered"] = True
            return "fake-conn"

        def __exit__(self, exc_type, exc, tb):
            captured["exited"] = True
            return False

    comparison = PeerComparison(
        target=PeerMetricRow(
            corp_code="1",
            stock_code="AAA001",
            corp_name="Target Co",
            sector="semiconductor",
            data_quality_score=95,
        ),
        peers=[
            PeerMetricRow(
                corp_code="2",
                stock_code="BBB001",
                corp_name="Peer Co",
                sector="semiconductor",
                market_cap=1_200_000,
                close_price=12_000,
                per=11.2,
                pbr=1.1,
                roe=0.12,
                revenue_growth=0.05,
                operating_margin=0.2,
                debt_ratio=0.4,
                data_quality_score=90,
            )
        ],
        score=78,
        peer_selection_summary="동일 섹터에서 비교 가능한 peer 1개를 선택했습니다.",
        peer_summary="Peer 대비 수익성과 밸류에이션이 양호합니다.",
        metric_definitions={"per": "market_cap / net_income", "score": "종합 점수"},
        relative_position={"valuation_percentile": 0.65, "data_quality_score": 95},
        evidence=["ROE가 peer 중앙값보다 높습니다."],
        data_quality_flags=["peer_count_below_minimum"],
        a1_peer_multiple_payload={"median_per": 11.2, "median_pbr": 1.1},
        warnings=["peer_count_below_minimum"],
    )

    def fake_get_connection():
        return FakeConnection()

    def fake_build_peer_comparison(conn, stock_code, sector):
        captured["conn"] = conn
        captured["stock_code"] = stock_code
        captured["sector"] = sector
        return comparison

    monkeypatch.setattr(competitor_module, "get_connection", fake_get_connection)
    monkeypatch.setattr(competitor_module, "build_peer_comparison", fake_build_peer_comparison)

    state = _state_with_curator()
    result_state = competitor_module.run_competitor(state)

    assert result_state is state
    assert captured == {
        "entered": True,
        "conn": "fake-conn",
        "stock_code": "AAA001",
        "sector": "semiconductor",
        "exited": True,
    }
    assert state.competitor is not None
    assert state.competitor.score == comparison.score
    assert state.competitor.peer_summary == comparison.peer_summary
    assert state.competitor.peers == [
        {
            "stock_code": "BBB001",
            "corp_code": "2",
            "corp_name": "Peer Co",
            "sector": "semiconductor",
            "market_cap": 1_200_000,
            "close_price": 12_000,
            "per": 11.2,
            "pbr": 1.1,
            "roe": 0.12,
            "revenue_growth": 0.05,
            "operating_margin": 0.2,
            "debt_ratio": 0.4,
            "data_quality_score": 90,
        }
    ]
    assert state.competitor.evidence == comparison.evidence
    assert state.competitor.peer_selection_summary == comparison.peer_selection_summary
    assert state.competitor.metric_definitions == comparison.metric_definitions
    assert state.competitor.relative_position == comparison.relative_position
    assert state.competitor.data_quality_flags == comparison.data_quality_flags
    assert state.competitor.a1_peer_multiple_payload == comparison.a1_peer_multiple_payload
    assert state.competitor.warnings == comparison.warnings


def test_run_competitor_raises_without_curator() -> None:
    state = AgentState(user_query="경쟁사 비교", user_profile=UserProfile(), portfolio=Portfolio())

    with pytest.raises(ValueError, match="curator result is required"):
        competitor_module.run_competitor(state)


def test_run_competitor_uses_explicit_mock_fallback_when_db_fails(monkeypatch) -> None:
    def failing_get_connection():
        raise RuntimeError("database is unavailable")

    monkeypatch.setattr(competitor_module, "get_connection", failing_get_connection)

    state = _state_with_curator()
    result_state = competitor_module.run_competitor(state)

    assert result_state is state
    assert state.competitor is not None
    assert not any("mock_data_fallback" in item for item in state.competitor.evidence)
    assert not any("fallback_reason" in warning for warning in state.competitor.warnings)
    assert any("삼성전자 PER" in item for item in state.competitor.evidence)
    assert any("SK하이닉스" in item for item in state.competitor.evidence)
    assert state.competitor.peer_selection_summary is not None
    assert "반도체 업종" in state.competitor.peer_selection_summary
    assert any("mock_data_fallback" in flag for flag in state.competitor.data_quality_flags)


def _mcp_records() -> list[dict]:
    return [
        {
            "stock_code": "AAA001",
            "corp_name": "Target Co",
            "base_date": "20260612",
            "close_price": 70000,
            "market_cap": 1_000_000,
            "per": 18.0,
            "pbr": 1.3,
            "roe": 0.11,
        },
        {
            "stock_code": "BBB001",
            "corp_name": "Peer B",
            "base_date": "20260612",
            "close_price": 60000,
            "market_cap": 1_100_000,
            "per": 12.0,
            "pbr": 1.0,
            "roe": 0.14,
        },
        {
            "stock_code": "CCC001",
            "corp_name": "Peer C",
            "base_date": "20260612",
            "close_price": 50000,
            "market_cap": 900_000,
            "per": 20.0,
            "pbr": 1.5,
            "roe": 0.09,
        },
    ]


def test_run_competitor_uses_mcp_live_data_when_db_fails(monkeypatch) -> None:
    """DB 실패 시 MCP 실시간 시세 경로가 mock보다 우선 사용되고, mock으로 오판되지 않는다."""
    from stock_agent.mcp_bridge import peer_data_client

    def failing_get_connection():
        raise ConnectionError("database is unavailable")

    monkeypatch.setattr(competitor_module, "get_connection", failing_get_connection)
    monkeypatch.setattr(competitor_module, "get_settings", lambda: _stub_settings(competitor_mcp_fallback_enabled=True))

    def fake_fetch(stock_code, sector=None, timeout=20.0):
        assert stock_code == "AAA001"
        return peer_data_client.McpPeerData(
            target_stock_code="AAA001",
            sector=sector,
            base_date="20260612",
            records=_mcp_records(),
        )

    monkeypatch.setattr(peer_data_client, "fetch_mcp_peer_data", fake_fetch)

    state = _state_with_curator()
    competitor_module.run_competitor(state)

    assert state.competitor is not None
    # 실데이터 경로: MCP 출처 플래그가 있고, mock 폴백 마커는 없어야 한다(guardrail 오판 방지).
    assert "mcp_live_market_data" in state.competitor.data_quality_flags
    assert not any("mock_data_fallback" in flag for flag in state.competitor.data_quality_flags)
    forbidden = ("mock", "데모용")
    assert not any(
        any(word in flag.lower() for word in forbidden) for flag in state.competitor.data_quality_flags
    )
    assert not any(
        any(word in w.lower() for word in ("mock", "fallback", "데모용")) for w in state.competitor.warnings
    )
    assert [p["stock_code"] for p in state.competitor.peers] == ["BBB001", "CCC001"]
    assert state.competitor.score > 0


def test_run_competitor_falls_back_to_mock_when_mcp_unavailable(monkeypatch) -> None:
    """MCP 경로가 실패하면 최후 보루인 하드코딩 mock으로 폴백한다."""
    from stock_agent.mcp_bridge import peer_data_client

    def failing_get_connection():
        raise ConnectionError("database is unavailable")

    monkeypatch.setattr(competitor_module, "get_connection", failing_get_connection)
    monkeypatch.setattr(competitor_module, "get_settings", lambda: _stub_settings(competitor_mcp_fallback_enabled=True))

    def failing_fetch(stock_code, sector=None, timeout=20.0):
        raise peer_data_client.McpUnavailableError("MCP 서버 기동 실패")

    monkeypatch.setattr(peer_data_client, "fetch_mcp_peer_data", failing_fetch)

    state = _state_with_curator()
    competitor_module.run_competitor(state)

    assert state.competitor is not None
    assert any("mock_data_fallback" in flag for flag in state.competitor.data_quality_flags)


def test_run_competitor_reraises_unexpected_internal_error(monkeypatch) -> None:
    class FakeConnection:
        def __enter__(self):
            return "fake-conn"

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_get_connection():
        return FakeConnection()

    def failing_build_peer_comparison(conn, stock_code, sector):
        raise ValueError("calculation contract changed")

    monkeypatch.setattr(competitor_module, "get_connection", fake_get_connection)
    monkeypatch.setattr(competitor_module, "build_peer_comparison", failing_build_peer_comparison)

    state = _state_with_curator()

    with pytest.raises(ValueError, match="calculation contract changed"):
        competitor_module.run_competitor(state)

    assert state.competitor is None
