# `src/stock_agent/mcp_bridge/` — Competitor MCP 데이터 브리지

루브릭 #6(MCP/A2A)의 **"외부 데이터 Tool 1개를 MCP 서버로 노출 + 실동작 1경로"** 를 충족하는
모듈입니다. Competitor Agent가 **DB에 연결하지 못했을 때**, 하드코딩 mock 대신 자체 MCP 서버를
**별도 자식 프로세스(stdio 트랜스포트)** 로 띄워 **pykrx 실시간 시세 기반 peer 비교**를 확보합니다.

> ⚠️ 트랜스포트는 in-process가 아니라 **진짜 stdio**입니다. 클라이언트가 `sys.executable -m
> peer_data_server`로 서버를 자식 프로세스로 실행하고 `initialize → tools/list → call_tool`
> 표준 핸드셰이크로 통신합니다. 호출 전 `tools/list`로 기대 Tool(`sector_roster`·`market_metrics`)을
> 발견하지 못하면 즉시 폴백 신호로 전환합니다.

## 구성

| 파일 | 역할 |
|------|------|
| `peer_roster.py` | 섹터별 비교군 후보(번들 정적 데이터, 외부 의존 없음). 반도체 섹터 기준 |
| `peer_data_server.py` | **FastMCP 서버**. pykrx로 시세·밸류에이션(PER/PBR/EPS/BPS/시총)을 조회해 Tool로 노출 |
| `peer_data_client.py` | **stdio MCP 클라이언트**. 서버를 자식 프로세스로 띄워 Tool 호출, 동기 래퍼 `fetch_mcp_peer_data` 제공 |

## 노출 MCP Tool

서버(`stock-agent-peer-data`)가 노출하는 Tool:

- `sector_roster(sector)` → `[{corp_code, stock_code, corp_name}]` (네트워크 불필요)
- `market_metrics(stock_codes, base_date="")` → `[{stock_code, corp_name, close_price, market_cap, per, pbr, roe, eps, bps}]` (pykrx 실시간)

> ROE는 pykrx가 직접 주지 않으므로 `EPS / BPS`로 근사합니다(둘 다 양수일 때만). DART 재무 파생
> 지표(매출성장률·영업이익률·부채비율)는 이 경로에서 제공되지 않아 결측 처리됩니다 — 정직한
> 데이터 품질 신호로 `*_missing` 플래그가 부여됩니다.

## 폴백 우선순위 (`agents/competitor.py`)

```
DB(psycopg) 성공  → 기존 실데이터 경로 (변경 없음)
DB 실패           → ① MCP 실시간 시세(실데이터)  ← 본 모듈
                  → ② 하드코딩 mock(최후 보루)
```

- `config.Settings.competitor_mcp_fallback_enabled`(기본 True)로 켜고 끕니다.
- `competitor_mcp_timeout_seconds`(기본 20s) 초과·서버 기동 실패·빈 결과는 모두 mock으로 양보합니다.
- MCP 결과는 **실데이터**이므로 `data_quality_flags`에 `mcp_live_market_data`/`db_unavailable_used_mcp`
  마커만 붙이고, guardrail `mock_data_audit`가 mock으로 오판하지 않도록 `"mock"`/`"fallback"`/`"데모용"`
  문자열을 의도적으로 배제합니다.

## 외부 노출 (A2A · 범용 소비)

이 서버는 Competitor 폴백 전용이 아니라 **표준 stdio MCP 서버**이므로, 다른 에이전트나
외부 MCP 클라이언트가 그대로 소비할 수 있습니다. 호출자는 서버 내부(pykrx·로스터·점수
엔진)를 알 필요 없이 공개 클라이언트 표면만 사용합니다.

### 범용 클라이언트 진입점 (`peer_data_client`)

| 함수 | 용도 |
|------|------|
| `discover_tools(timeout)` | `initialize → tools/list` 핸드셰이크로 노출 Tool 발견 |
| `call_mcp_tool(tool_name, arguments, timeout)` | **임의 Tool을 1회 호출**(범용 A2A 진입점). 미발견·기동 실패·타임아웃은 `McpUnavailableError`로 통일 |
| `fetch_mcp_peer_data(...)` | Competitor 폴백 전용 고수준 헬퍼(위 진입점을 조합) |

```python
from stock_agent.mcp_bridge.peer_data_client import discover_tools, call_mcp_tool

discover_tools()                                   # [{name, description}, ...]
call_mcp_tool("sector_roster", {"sector": "반도체"})  # 정적 데이터(오프라인 동작)
call_mcp_tool("market_metrics", {"stock_codes": ["005930"]})  # pykrx 실시간
```

### 외부 MCP 클라이언트 등록 (Claude Desktop / Cursor 등)

표준 stdio 서버이므로 어떤 MCP 클라이언트의 `mcpServers` 설정에도 등록할 수 있습니다.

```json
{
  "mcpServers": {
    "stock-agent-peer-data": {
      "command": "python",
      "args": ["-m", "stock_agent.mcp_bridge.peer_data_server"],
      "env": { "PYTHONPATH": "src" }
    }
  }
}
```

### 외부 소비자 데모

```bash
# 공개 API(discover_tools·call_mcp_tool)만으로 두 Tool을 소비하는 A2A 시나리오
PYTHONPATH=src python scripts/mcp_external_consumer_demo.py 반도체
```

`sector_roster` round-trip은 네트워크 없이 동작하므로 시연·CI에서 그대로 재현됩니다.

## 설치 / 실행

```bash
pip install -e .[mcp]          # mcp SDK + pykrx (선택 의존성)

# 서버 단독 실행(stdio)
python -m stock_agent.mcp_bridge.peer_data_server

# 핸드셰이크 데모 (발표·시연용, KRX 네트워크 불필요 — sector_roster + tools/list)
PYTHONPATH=src python scripts/mcp_peer_handshake_demo.py 반도체

# 클라이언트 직접 호출(스모크)
python -c "from stock_agent.mcp_bridge.peer_data_client import fetch_mcp_peer_data; \
print(fetch_mcp_peer_data('005930', sector='반도체').records[:2])"
```

데모는 `initialize → tools/list → call_tool(sector_roster)` round-trip을 출력하므로,
강사 시연·발표 스크린샷에 그대로 쓸 수 있습니다(`sector_roster`는 정적 데이터라 오프라인 동작).

`mcp`/`pykrx` 미설치 환경에서도 순수 헬퍼(`peer_roster`, `peer_data_server`의 매핑 함수)는
import·테스트 가능하며, 클라이언트는 `is_available()`이 False를 반환해 Competitor가 mock으로
폴백합니다. 따라서 DB 정상 경로와 CI에는 영향이 없습니다.

## 테스트

- `tests/mcp_bridge/test_mcp_bridge.py` — 로스터·서버 순수 헬퍼·클라이언트 헬퍼(네트워크/실서버 미사용)
- `tests/mcp_bridge/test_mcp_handshake.py` — **실제 stdio round-trip 자동 검증**. `discover_tools()`로 `tools/list`를 확인하고, **범용 `call_mcp_tool()`** 로 `sector_roster` round-trip + 미발견 Tool의 `McpUnavailableError` 전환까지 검증(오프라인 동작, `mcp` 미설치 시 skip)
- `tests/tools/test_peer_tool.py` — `build_comparison_from_market_rows`(실시간 레코드 → PeerComparison)
- `tests/agents/test_competitor_agent.py` — DB실패→MCP실데이터 / MCP실패→mock 3단 폴백 체인

> `tools/list` 핸드셰이크와 `sector_roster` round-trip은 **자동 테스트**로 검증됩니다(네트워크 불필요).
> `market_metrics`의 pykrx 실데이터만 KRX 접속이 필요해, 접속 불가 환경에서는 통일된
> `McpUnavailableError`로 mock 폴백합니다(크래시 없음).
