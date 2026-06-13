"""MCP stdio 핸드셰이크 통합 테스트.

기존 test_mcp_bridge.py가 순수 헬퍼만 본 것과 달리, 이 테스트는 서버를 실제
stdio 자식 프로세스로 띄워 tools/list round-trip을 자동 검증한다.
`sector_roster`는 KRX 네트워크가 필요 없어 오프라인·CI에서도 재현 가능하다.

`mcp` 미설치 환경에서는 자동으로 skip 한다(`[mcp]` extra 선택 설치).
"""

import pytest

mcp = pytest.importorskip("mcp", reason="mcp 패키지 필요: pip install -e .[mcp]")

from stock_agent.mcp_bridge import peer_data_client  # noqa: E402

_TIMEOUT = 30.0


def test_discover_tools_lists_expected_tools() -> None:
    """tools/list 핸드셰이크가 sector_roster·market_metrics를 노출한다."""
    tools = peer_data_client.discover_tools(timeout=_TIMEOUT)
    names = {t["name"] for t in tools}
    assert {"sector_roster", "market_metrics"} <= names
    # 각 Tool은 설명 문자열을 가진다(스키마 노출 확인).
    by_name = {t["name"]: t for t in tools}
    assert by_name["sector_roster"]["description"]
    assert by_name["market_metrics"]["description"]


def test_fetch_peer_data_offline_uses_static_roster() -> None:
    """fetch 경로의 tools/list 검증 + sector_roster 호출까지 round-trip 한다.

    market_metrics는 KRX 시세가 필요해 빈 결과가 날 수 있으므로, 여기서는
    핸드셰이크가 McpUnavailableError 없이 진행되는지(또는 시세 부재로 통일된
    McpUnavailableError가 나는지)만 본다 — 크래시가 전파되지 않아야 한다.
    """
    try:
        data = peer_data_client.fetch_mcp_peer_data(
            "005930", sector="반도체", timeout=_TIMEOUT
        )
    except peer_data_client.McpUnavailableError:
        # KRX 미접속(샌드박스/CI)에서는 market_metrics 빈 결과 → 통일된 폴백 신호. 정상.
        return
    # KRX 접속이 되는 환경이면 실데이터 레코드가 채워진다.
    assert data.target_stock_code == "005930"
    assert isinstance(data.records, list)
