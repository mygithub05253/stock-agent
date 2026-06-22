# 인터페이스 / API 명세서 (Interface Specification)

> 기준 코드(SSOT): [`pipeline_11node_groundtruth.md`](../architecture/pipeline_11node_groundtruth.md) · 계약 스키마: `src/stock_agent/schemas/analysis.py`
> 작성: PM 문서화 트랙 (2026-06-20, 코드 읽기 기반 · 코드 미수정)
> HTML 렌더: [`docs/api.html`](../api.html)

본 문서는 stock-agent의 **인터페이스 계약**을 정의한다. 이 시스템은 REST 서버가 아니라 **LangGraph 노드 간 인터페이스 + MCP Tool + 산출물 인터페이스**로 구성된다. 강사 항목4가 "인터페이스 정의서 부재"로 부여한 캡을 해소한다(유스케이스는 [`usecase_spec.md`](../usecase/usecase_spec.md)).

---

## 1. 인터페이스 계약 원칙

1. **단일 상태 객체(AgentState)**: 모든 내부 노드는 자유 대화가 아니라 `AgentState`(Pydantic)를 읽고 일부 필드를 채워 반환한다(`schemas/analysis.py:209-226`). 노드 함수 시그니처는 전부 `run_*(state: AgentState) -> AgentState`.
2. **Pydantic 검증**: 입출력은 Pydantic 모델로 타입·범위가 강제된다(예: `score ge=0 le=100`, `signal ∈ {BUY,HOLD,SELL}`).
3. **부분 채움 허용**: 워커 결과 필드는 `| None`. 실패 시 None으로 남고 Strategist가 가용 필드만 합성.
4. **외부 인터페이스 2종**: ① MCP Tool(외부에 peer 데이터 노출/소비) ② 산출물(HTML/Excel/PDF 다운로드).

---

## 2. 핵심 데이터 스키마 (`schemas/analysis.py`)

| 모델 | 주요 필드 | 용도 |
|---|---|---|
| `UserProfile` | risk_tolerance(low/medium/high), investment_horizon_months, max_drawdown_tolerance, liquidity_need_level, preferred_sectors | 투자성향 |
| `Portfolio` | holdings[`Holding`], cash_weight, (파생) total_market_value·sector_weights | 보유 현황 |
| `Holding` | stock_code, corp_name, sector, weight, avg_price, qty, current_price, (파생) cost_basis·market_value | 종목 단위 |
| `UserRequest` | raw_query, intent(5종), target_stock_code, analysis_scope(single_stock/portfolio/sector), urgency_reason, requested_depth(summary/standard/deep) | 분류 결과 |
| `CuratorResult` | intent, corp_name, stock_code, corp_code, sector, candidates[], warnings[] | 큐레이션 |
| `QuantResult` | score, valuation_signal, metrics{}, reasons[], risks[] | 정량 |
| `QualResult` | score, sentiment(pos/neu/neg), event_types[], evidence[], risks[] | 정성 |
| `CompetitorResult` | score, peer_summary, peers[], evidence[], relative_position{}, data_quality_flags[] | Peer |
| `MacroResult` | score, macro_signal, indicators{}, rate_of_change{}, reasons[], risks[], sector, as_of_date | 거시 |
| `StrategistResult` | signal, confidence, suitability, headline, key_reasons[], risks[], next_actions[], degraded, contributing_agents[], fallback_used | 합성 |
| `GuardrailResult` | passed, warnings[], revised_headline, disclaimer, needs_revision, risk_level, checks[], trace_id | 검증 |
| `AnalysisOutput` | tier1(`Tier1Result`), tier2{}, tier3{}, state | 최종 출력 |

---

## 3. 내부 노드 인터페이스 계약 (11노드)

각 노드는 `AgentState`에서 **읽는 필드**와 **쓰는 필드**가 정해져 있다(`pipeline.py`의 `_patch_from_agent`/`_node` 기준).

| # | 노드 | 읽는 필드(입력) | 쓰는 필드(출력) | 출력 스키마 |
|---|---|---|---|---|
| 1 | curator | user_query, portfolio, user_profile | curator | `CuratorResult` |
| 2 | classifier | user_query, curator | user_request, graph_route | `UserRequest` |
| 3 | quant | curator, portfolio | quant | `QuantResult` |
| 4 | qual | curator | qual | `QualResult` |
| 5 | competitor | curator | competitor | `CompetitorResult` |
| 6 | macro | curator | macro | `MacroResult` |
| 7 | strategist | quant, qual, competitor, macro, portfolio, user_profile | strategist | `StrategistResult` |
| 8 | investment_analyst | strategist | strategist(갱신) | `StrategistResult` |
| 9 | guardrail | strategist | guardrail | `GuardrailResult` |
| 10 | guardrail_apply | strategist, guardrail | strategist, guardrail | (갱신) |
| 11 | renderer | state 전체 | rendered_report | `RenderedReport` |

**라우팅 계약** (`graph_route`, classifier 산출):
```jsonc
{
  "analysis_scope": "single_stock | portfolio | sector",
  "urgency_reason": "surge | drop | earnings | news | general | null",
  "requested_depth": "summary | standard | deep",
  "summary_only": true,                       // requested_depth == "summary"
  "worker_plan": ["quant", "qual", "competitor", "macro?"]  // macro는 조건부
}
```

**스트리밍 이벤트 계약** (`stream_phase1_analysis_events`, `pipeline.py:522-555`):
```jsonc
{ "type": "node|complete", "node": "<코드명>", "label": "<UI 라벨>",
  "status": "done|error", "detail": "<요약>", "state": "<AgentState>" }
```

---

## 4. MCP Tool 인터페이스 (외부 노출/소비)

서버: `FastMCP("stock-agent-peer-data")` · stdio · `python -m stock_agent.mcp_bridge.peer_data_server` (`peer_data_server.py:150-173`)

### 4.1 `sector_roster`
- **입력**: `sector: str` (예: `"반도체"`)
- **출력**: `list[{ "stock_code": str, "corp_name": str }]` — 섹터 비교군 후보
- **예시**: `call_tool("sector_roster", {"sector": "반도체"})` → roster 다건

### 4.2 `market_metrics`
- **입력**: `stock_codes: list[str]`, `base_date: str = ""`(미지정 시 최근 영업일)
- **출력**: `list[record]`, record 스키마(`build_metric_record`, `peer_data_server.py:46-77`):
```jsonc
{
  "stock_code": "000660", "corp_name": "SK하이닉스", "base_date": "2026-05-21",
  "close_price": 201000, "market_cap": 146000000000000,
  "per": 12.3, "pbr": 1.8, "roe": 0.14,   // 0 이하·결측은 null (PER/PBR 0 = 결측 신호)
  "eps": 16300, "bps": 110000              // roe는 EPS/BPS 근사(둘 다 양수일 때만)
}
```
- **소비처**: Competitor 노드의 DB 실패 시 폴백 경로(`competitor.py:160-208`).
- **장애 계약**: `mcp`/`pykrx` 미설치·조회 실패 → `RuntimeError` → 상위에서 mock 폴백.

### 4.3 클라이언트 핸드셰이크
`peer_data_client.py`의 `ClientSession.initialize()` + `list_tools()`로 stdio 핸드셰이크 후 `call_tool` round-trip. 검증: `tests/mcp_bridge/test_mcp_handshake.py`.

---

## 5. 산출물(출력) 인터페이스

`AnalysisOutput`(`schemas/analysis.py:229-233`):

| 계층 | 형식 | 내용 |
|---|---|---|
| **Tier 1** | `Tier1Result` | signal(BUY/HOLD/SELL), confidence, suitability, headline, disclaimer |
| **Tier 2** | `dict[str, list[str]|str]` | 정량 근거·정성 근거·Peer 비교·거시경제·포트폴리오 적합도·리스크 |
| **Tier 3** | `dict[str, str]` | PB 리포트(PDF)·밸류에이션(Excel)·산업/뉴스(HTML) 다운로드 |

**다운로드 인터페이스**(`streamlit_app.py`): `_build_html_report`(bytes) · `_build_excel_report`(xlsx) · `_build_pdf_report`(pdf). DB 미저장, 사용자 디바이스로 직접 다운로드.

---

## 6. 외부 데이터 인터페이스 (요약)

| 소스 | 진입 | 인터페이스 | 실패 계약 |
|---|---|---|---|
| DART | `tools/` | 재무·공시 조회 | mock / fallback evidence |
| pykrx/KRX | `tools/`·MCP | 시세·밸류에이션 | RuntimeError→mock |
| 뉴스 | `datas/news/`·`rag/` | RAG 검색(Hybrid RRF) | fallback_news_docs |
| ECOS | `datas/macro/` | 거시지표 | mock |
| LLM(OpenRouter/GLM) | `llm/` | 분류·합성·보정 | rule-based / conservative |

> 외부 인터페이스의 모든 실패는 예외를 전파하지 않고 폴백 계약으로 흡수된다(유스케이스 예외 흐름 E1~E6 참조).

---

## 7. 정합 추적
- 노드 입출력 계약이 바뀌면 SSOT → 본 문서 → `api.html` 순으로 동기화.
- MCP Tool 스키마는 `peer_data_server.py`를, 데이터 모델은 `schemas/analysis.py`를 정본으로 한다.
