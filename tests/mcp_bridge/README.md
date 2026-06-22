# `tests/mcp_bridge/` - MCP 브리지 계약 검증

> Competitor peer 데이터 서버·클라이언트가 표준 MCP 핸드셰이크와 Tool 계약을 지키는지 검증합니다.

## 핵심 범위

- 서버 Tool 목록과 입력 schema
- stdio 자식 프로세스 초기화·종료
- 범용 클라이언트 `discover_tools`와 `call_mcp_tool`
- 네트워크 없이 동작하는 sector roster 경로
- 오류·timeout 시 상위 Competitor fallback에 필요한 예외 계약

## 기술 스택과 동작

pytest, `mcp`, asyncio, subprocess를 사용합니다. 실제 KRX 호출 대신 결정적인 roster와 monkeypatch를 우선해 CI에서 재현성을 유지합니다.

## 실행

```bash
pip install -e .[mcp,dev]
python -m pytest tests/mcp_bridge -v
```

상세 구조는 [`src/stock_agent/mcp_bridge/README.md`](../../src/stock_agent/mcp_bridge/README.md)를 참고합니다.
