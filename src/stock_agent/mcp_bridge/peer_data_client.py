"""Competitor 폴백에서 자체 MCP 서버를 호출하는 stdio 클라이언트.

`peer_data_server`를 자식 프로세스로 띄워(stdio) sector_roster·market_metrics Tool을 호출하고,
peer 비교 빌더가 쓸 지표 레코드 목록을 반환한다.

- 동기 진입점: `fetch_mcp_peer_data(...)` — 내부에서 asyncio 이벤트 루프를 생성/종료.
- `mcp` 미설치, 서버 기동 실패, 타임아웃, 빈 결과는 모두 `McpUnavailableError`로 통일해
  Competitor가 다음 폴백(하드코딩 mock)으로 넘어갈 수 있게 한다.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from stock_agent.mcp_bridge.peer_roster import roster_with_target

_SERVER_MODULE = "stock_agent.mcp_bridge.peer_data_server"
_DEFAULT_TIMEOUT_SECONDS = 20.0

# 이 패키지가 위치한 src 루트(.../src). editable 설치 없이 src 레이아웃으로 실행하는
# 개발 환경에서, 서버 자식 프로세스가 stock_agent 패키지를 import할 수 있도록 전달한다.
_SRC_ROOT = str(Path(__file__).resolve().parents[2])


def _child_env() -> dict[str, str]:
    """서버 자식 프로세스용 환경 변수. 현재 환경을 상속하되 PYTHONPATH에 src 루트를 보강한다."""
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    paths = [_SRC_ROOT, *existing.split(os.pathsep)] if existing else [_SRC_ROOT]
    # 중복 제거(순서 보존)
    env["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(p for p in paths if p))
    return env


class McpUnavailableError(RuntimeError):
    """MCP 경로로 실데이터를 확보하지 못했을 때 발생(상위에서 mock 폴백으로 전환)."""


@dataclass
class McpPeerData:
    target_stock_code: str
    sector: str | None
    base_date: str
    records: list[dict[str, Any]] = field(default_factory=list)


def is_available() -> bool:
    """mcp 클라이언트 패키지가 설치되어 있는지."""
    try:
        import mcp  # noqa: F401
        from mcp.client.stdio import stdio_client  # noqa: F401

        return True
    except ModuleNotFoundError:
        return False


def _extract_payload(result: Any) -> Any:
    """CallToolResult에서 Tool 반환값(JSON)을 꺼낸다."""
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict) and "result" in structured:
        return structured["result"]
    content = getattr(result, "content", None) or []
    for item in content:
        text = getattr(item, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                continue
    return None


def _server_params():
    """서버를 자식 프로세스(stdio)로 띄우기 위한 공통 파라미터."""
    from mcp import StdioServerParameters

    return StdioServerParameters(
        command=sys.executable,
        args=["-m", _SERVER_MODULE],
        env=_child_env(),
    )


def _tool_names(list_tools_result: Any) -> list[str]:
    """list_tools 응답에서 Tool 이름 목록을 안전하게 추출한다."""
    tools = getattr(list_tools_result, "tools", None) or []
    return [getattr(t, "name", "") for t in tools if getattr(t, "name", "")]


async def _adiscover_tools(timeout: float) -> list[dict[str, Any]]:
    """서버와 stdio 핸드셰이크 후 tools/list 결과(이름·설명)를 반환한다.

    market_metrics(KRX 시세) 같은 네트워크 의존 Tool을 호출하지 않으므로
    오프라인·CI에서도 MCP 트랜스포트 round-trip을 그대로 실증할 수 있다.
    """
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    params = _server_params()

    async def _run() -> list[dict[str, Any]]:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                tools = getattr(listed, "tools", None) or []
                return [
                    {"name": getattr(t, "name", ""), "description": getattr(t, "description", "") or ""}
                    for t in tools
                    if getattr(t, "name", "")
                ]

    return await asyncio.wait_for(_run(), timeout=timeout)


def discover_tools(timeout: float = _DEFAULT_TIMEOUT_SECONDS) -> list[dict[str, Any]]:
    """동기 진입점: tools/list 핸드셰이크 결과를 반환한다(데모·통합 테스트용).

    실패 시 `McpUnavailableError`로 통일한다.
    """
    if not is_available():
        raise McpUnavailableError("mcp 패키지가 설치되어 있지 않습니다. `pip install -e .[mcp]`")
    try:
        return asyncio.run(_adiscover_tools(timeout))
    except McpUnavailableError:
        raise
    except (asyncio.TimeoutError, TimeoutError) as exc:
        raise McpUnavailableError(f"MCP 서버 응답 타임아웃({timeout}s)") from exc
    except Exception as exc:  # noqa: BLE001 - 서버 기동·통신 실패를 단일 신호로 통일
        raise McpUnavailableError(f"MCP tools/list 실패: {exc.__class__.__name__}: {exc}") from exc


async def _afetch(
    stock_code: str,
    sector: str | None,
    base_date: str | None,
    timeout: float,
) -> McpPeerData:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    params = _server_params()

    async def _run() -> McpPeerData:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # MCP 표준 흐름: 호출 전 tools/list로 사용 가능한 Tool을 발견(handshake)한다.
                # 기대 Tool이 없으면 즉시 폴백 신호로 전환해 잘못된 서버에 call하지 않는다.
                listed = await session.list_tools()
                available = set(_tool_names(listed))
                missing = {"sector_roster", "market_metrics"} - available
                if missing:
                    raise McpUnavailableError(
                        f"MCP 서버에 기대 Tool이 없습니다: {sorted(missing)} (발견: {sorted(available)})"
                    )

                # 비교군 후보 코드(대상 포함) 구성. 서버 로스터를 우선 시도하되,
                # 비어 있으면 클라이언트 측 로스터로 보강한다.
                roster_result = await session.call_tool("sector_roster", {"sector": sector or ""})
                roster = _extract_payload(roster_result) or []
                codes = [entry["stock_code"] for entry in roster if entry.get("stock_code")]
                if not codes:
                    codes = [entry["stock_code"] for entry in roster_with_target(sector, stock_code)]
                if stock_code not in codes:
                    codes = [stock_code, *codes]
                # 중복 제거(입력 순서 보존)
                codes = list(dict.fromkeys(codes))

                metrics_result = await session.call_tool(
                    "market_metrics",
                    {"stock_codes": codes, "base_date": base_date or ""},
                )
                records = _extract_payload(metrics_result) or []
                if not isinstance(records, list) or not records:
                    raise McpUnavailableError("MCP market_metrics가 빈 결과를 반환했습니다.")

                base = str(records[0].get("base_date") or base_date or "")
                return McpPeerData(
                    target_stock_code=stock_code,
                    sector=sector,
                    base_date=base,
                    records=records,
                )

    return await asyncio.wait_for(_run(), timeout=timeout)


def fetch_mcp_peer_data(
    stock_code: str,
    sector: str | None = None,
    base_date: str | None = None,
    timeout: float = _DEFAULT_TIMEOUT_SECONDS,
) -> McpPeerData:
    """동기 진입점. 실패 시 `McpUnavailableError`."""
    if not is_available():
        raise McpUnavailableError("mcp 패키지가 설치되어 있지 않습니다. `pip install -e .[mcp]`")

    try:
        return asyncio.run(_afetch(stock_code, sector, base_date, timeout))
    except McpUnavailableError:
        raise
    except (asyncio.TimeoutError, TimeoutError) as exc:
        raise McpUnavailableError(f"MCP 서버 응답 타임아웃({timeout}s)") from exc
    except Exception as exc:  # noqa: BLE001 - 서버 기동·통신 실패를 단일 신호로 통일
        raise McpUnavailableError(f"MCP 데이터 조회 실패: {exc.__class__.__name__}: {exc}") from exc
