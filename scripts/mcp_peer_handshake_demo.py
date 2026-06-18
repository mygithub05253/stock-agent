"""Competitor MCP 브리지 핸드셰이크 데모 (발표·강사 시연용).

자체 FastMCP 서버(`peer_data_server`)를 stdio 자식 프로세스로 띄워
① tools/list 핸드셰이크로 노출 Tool을 발견하고
② 네트워크가 필요 없는 `sector_roster` Tool을 실제 호출해 결과를 출력한다.

`sector_roster`는 정적 비교군 데이터라 KRX 네트워크 없이도 동작하므로,
오프라인·CI·샌드박스에서 MCP 트랜스포트 round-trip을 그대로 재현할 수 있다.
(실시간 시세 `market_metrics`는 pykrx/KRX 접속이 필요해 이 데모에서는 호출하지 않는다.)

실행:
    python scripts/mcp_peer_handshake_demo.py [섹터]
    예) python scripts/mcp_peer_handshake_demo.py 반도체

요구: `pip install -e .[mcp]` (mcp 패키지). 미설치 시 안내 후 종료한다.
"""

from __future__ import annotations

import asyncio
import sys

from stock_agent.mcp_bridge import peer_data_client


async def _run(sector: str) -> int:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    params = peer_data_client._server_params()

    print("=" * 60)
    print("stock-agent · Competitor MCP 핸드셰이크 데모")
    print("=" * 60)
    print(f"서버 모듈 : {peer_data_client._SERVER_MODULE}")
    print(f"트랜스포트: stdio (자식 프로세스)")
    print(f"대상 섹터 : {sector}")
    print("-" * 60)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            # 1) initialize 핸드셰이크
            init = await session.initialize()
            server_name = getattr(getattr(init, "serverInfo", None), "name", "?")
            print(f"[initialize] 연결 성공 · server = {server_name}")

            # 2) tools/list 핸드셰이크
            listed = await session.list_tools()
            tools = getattr(listed, "tools", None) or []
            print(f"[tools/list] 노출 Tool {len(tools)}개:")
            for tool in tools:
                name = getattr(tool, "name", "?")
                desc = (getattr(tool, "description", "") or "").strip()
                print(f"   - {name}: {desc}")

            # 3) 오프라인 안전 Tool 실제 호출
            print("-" * 60)
            print(f'[call_tool] sector_roster(sector="{sector}")')
            result = await session.call_tool("sector_roster", {"sector": sector})
            roster = peer_data_client._extract_payload(result) or []
            if not roster:
                print("   (빈 결과 — 알 수 없는 섹터일 수 있습니다)")
            for entry in roster:
                print(f"   · {entry.get('stock_code')} {entry.get('corp_name', '')}")

    print("=" * 60)
    print("핸드셰이크 완료 — MCP stdio round-trip 정상 (tools/list + call_tool)")
    print("=" * 60)
    return 0


def main() -> int:
    # Windows 콘솔(cp949)에서도 한글·em dash 출력이 깨지지 않도록 stdout을 utf-8로 고정한다.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 - 재설정 미지원 환경은 그대로 진행
        pass

    sector = sys.argv[1] if len(sys.argv) > 1 else "반도체"

    if not peer_data_client.is_available():
        print("mcp 패키지가 설치되어 있지 않습니다. `pip install -e .[mcp]` 후 다시 실행하세요.")
        return 1

    try:
        return asyncio.run(_run(sector))
    except Exception as exc:  # noqa: BLE001 - 데모 실행 실패를 사용자에게 친절히 안내
        print(f"데모 실행 실패: {exc.__class__.__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
