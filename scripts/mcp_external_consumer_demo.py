"""MCP 외부 소비자(A2A) 데모 — 공개 클라이언트 표면만으로 서버 Tool을 소비한다.

Competitor 폴백 흐름(`fetch_mcp_peer_data`)과 무관하게, **다른 에이전트나 외부 프로세스가
이 stdio MCP 서버를 범용 엔드포인트로 호출**하는 시나리오를 재현한다. 호출자는
`peer_data_client`의 공개 API(`discover_tools`·`call_mcp_tool`)만 사용하며, 서버 내부 구현
(pykrx·로스터·peer 점수 엔진)은 전혀 알 필요가 없다 — 이것이 MCP "외부 노출"의 핵심이다.

흐름:
  1. discover_tools()            : initialize → tools/list 로 노출 Tool 발견
  2. call_mcp_tool(sector_roster): 네트워크 불필요(정적 로스터) — 오프라인·CI에서도 동작
  3. call_mcp_tool(market_metrics): pykrx/KRX 실시간 — 접속 불가 시 폴백 신호로 친절히 안내

실행:
    python scripts/mcp_external_consumer_demo.py [섹터]
    예) python scripts/mcp_external_consumer_demo.py 반도체

요구: `pip install -e .[mcp]` (mcp 패키지). 미설치 시 안내 후 종료한다.
"""

from __future__ import annotations

import sys

from stock_agent.mcp_bridge import peer_data_client
from stock_agent.mcp_bridge.peer_data_client import McpUnavailableError


def main() -> int:
    # Windows 콘솔(cp949)에서도 한글 출력이 깨지지 않도록 stdout을 utf-8로 고정한다.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 - 재설정 미지원 환경은 그대로 진행
        pass

    sector = sys.argv[1] if len(sys.argv) > 1 else "반도체"

    if not peer_data_client.is_available():
        print("mcp 패키지가 설치되어 있지 않습니다. `pip install -e .[mcp]` 후 다시 실행하세요.")
        return 1

    print("=" * 64)
    print("stock-agent · MCP 외부 소비자(A2A) 데모 — 공개 API만 사용")
    print("=" * 64)
    print(f"서버 모듈 : {peer_data_client._SERVER_MODULE}")
    print(f"트랜스포트: stdio (자식 프로세스)")
    print("-" * 64)

    # 1) tools/list 핸드셰이크
    try:
        tools = peer_data_client.discover_tools()
    except McpUnavailableError as exc:
        print(f"tools/list 실패: {exc}")
        return 1
    print(f"[discover_tools] 노출 Tool {len(tools)}개:")
    for tool in tools:
        print(f"   - {tool['name']}: {tool['description']}")

    # 2) 오프라인 안전 Tool 호출(범용 진입점)
    print("-" * 64)
    print(f'[call_mcp_tool] sector_roster(sector="{sector}")')
    roster = peer_data_client.call_mcp_tool("sector_roster", {"sector": sector}) or []
    for entry in roster:
        print(f"   · {entry.get('stock_code')} {entry.get('corp_name', '')}")
    codes = [e["stock_code"] for e in roster if e.get("stock_code")][:3]

    # 3) 실시간 시세 Tool 호출(네트워크 의존 — 실패는 폴백 신호로 안내)
    print("-" * 64)
    print(f"[call_mcp_tool] market_metrics(stock_codes={codes})")
    try:
        metrics = peer_data_client.call_mcp_tool("market_metrics", {"stock_codes": codes}) or []
        for record in metrics:
            print(
                f"   · {record.get('stock_code')} {record.get('corp_name', '')} "
                f"PER={record.get('per')} PBR={record.get('pbr')} ROE={record.get('roe')}"
            )
    except McpUnavailableError as exc:
        print(f"   (KRX 실시간 시세 조회 불가 — 오프라인/샌드박스에서는 정상입니다: {exc})")

    print("=" * 64)
    print("외부 소비자 round-trip 완료 — 공개 API(discover_tools·call_mcp_tool)만으로 소비")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
