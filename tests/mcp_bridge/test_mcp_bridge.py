"""mcp_bridge 단위 테스트.

실제 MCP 서버 기동·pykrx 네트워크 호출 없이 순수 헬퍼만 검증한다.
(MCP 트랜스포트 round-trip 자체는 수동/통합 검증 영역 — README 참고)
"""

from stock_agent.mcp_bridge import peer_data_client, peer_data_server, peer_roster


# ----- peer_roster -----

def test_get_sector_roster_returns_semiconductor_codes() -> None:
    codes = [e["stock_code"] for e in peer_roster.get_sector_roster("반도체")]
    assert "005930" in codes
    assert "000660" in codes
    assert len(codes) >= 3


def test_normalize_sector_maps_aliases() -> None:
    assert peer_roster.normalize_sector("semiconductor") == "반도체"
    assert peer_roster.normalize_sector("SEMI") == "반도체"
    assert peer_roster.normalize_sector(None) is None


def test_roster_with_target_prepends_unknown_target() -> None:
    roster = peer_roster.roster_with_target("금융", "105560")
    assert roster[0]["stock_code"] == "105560"


def test_roster_with_target_keeps_known_target_once() -> None:
    roster = peer_roster.roster_with_target("반도체", "005930")
    codes = [e["stock_code"] for e in roster]
    assert codes.count("005930") == 1


# ----- peer_data_server 순수 헬퍼 -----

def test_build_metric_record_derives_roe_from_eps_bps() -> None:
    record = peer_data_server.build_metric_record(
        "005930", "삼성전자", "20260612",
        {"종가": 70000, "시가총액": 420_000_000_000_000},
        {"PER": 18.4, "PBR": 1.35, "EPS": 5000, "BPS": 50000},
    )
    assert record["per"] == 18.4
    assert record["pbr"] == 1.35
    assert record["roe"] == 0.1  # 5000 / 50000
    assert record["market_cap"] == 420_000_000_000_000


def test_build_metric_record_normalizes_zero_to_none() -> None:
    record = peer_data_server.build_metric_record(
        "000001", "적자기업", "20260612",
        {"종가": 1000, "시가총액": 0},
        {"PER": 0, "PBR": 0, "EPS": 0, "BPS": 0},
    )
    assert record["per"] is None
    assert record["pbr"] is None
    assert record["roe"] is None
    assert record["market_cap"] == 0


def test_metrics_from_frames_handles_missing_tickers() -> None:
    records = peer_data_server.metrics_from_frames(
        ["005930", "999999"],
        "20260612",
        cap_by_ticker={"005930": {"종가": 70000, "시가총액": 100}},
        fund_by_ticker={"005930": {"PER": 10, "PBR": 1, "EPS": 100, "BPS": 1000}},
        names={"005930": "삼성전자"},
    )
    assert records[0]["corp_name"] == "삼성전자"
    assert records[0]["per"] == 10
    # 매핑에 없는 티커는 결측 레코드로 채워진다(크래시 없음)
    assert records[1]["stock_code"] == "999999"
    assert records[1]["per"] is None
    assert records[1]["market_cap"] is None


# ----- peer_data_client 순수 헬퍼 -----

def test_extract_payload_prefers_structured_content() -> None:
    class FakeResult:
        structuredContent = {"result": [{"stock_code": "005930"}]}
        content = []

    payload = peer_data_client._extract_payload(FakeResult())
    assert payload == [{"stock_code": "005930"}]


def test_extract_payload_parses_text_content() -> None:
    class FakeText:
        text = '[{"stock_code": "000660"}]'

    class FakeResult:
        structuredContent = None
        content = [FakeText()]

    payload = peer_data_client._extract_payload(FakeResult())
    assert payload == [{"stock_code": "000660"}]


def test_child_env_prepends_src_root() -> None:
    env = peer_data_client._child_env()
    assert peer_data_client._SRC_ROOT in env["PYTHONPATH"].split(__import__("os").pathsep)


def test_fetch_raises_when_mcp_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(peer_data_client, "is_available", lambda: False)
    try:
        peer_data_client.fetch_mcp_peer_data("005930", sector="반도체")
    except peer_data_client.McpUnavailableError:
        pass
    else:  # pragma: no cover
        raise AssertionError("McpUnavailableError가 발생해야 합니다.")
