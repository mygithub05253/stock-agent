# Competitor Agent Core-First MVP Design

| Item | Value |
|------|-------|
| Date | 2026-05-26 |
| Branch | `codex/competitor-agent-design` |
| Status | Approved design |
| Owner Context | Competitor Agent 담당자, PM, agent/backend contributors |
| Related Specs | `docs/functional-spec/advanced/A3_peer_comparison_spec_v0.9.md`, `docs/architecture/multi_agent_architecture.md`, `docs/architecture/system_flow.md`, `docs/architecture/erd.md` |

---

## 1. Decision

Competitor Agent의 1차 MVP는 **Core-first 실사용형**으로 구현한다.

이번 범위는 Streamlit UI까지 한 번에 붙이는 큰 PR이 아니라, 다른 agent가 의존할 수 있는 계산 코어와 계약을 먼저 고정하는 PR이다. `company`, `stock_price`, `financial_statement`에 있는 실제 DB 데이터를 사용해 국내 같은 섹터 peer를 추출하고, PER/PBR/ROE/성장률/마진 기반 상대 위치와 competitor score를 계산한다.

UI는 다음 PR에서 붙인다. 이번 PR은 계산 신뢰도, schema 안정성, 테스트, 실험 노트북, PM 문서를 우선한다.

---

## 2. Goals

- `CuratorResult`의 `stock_code`, `corp_code`, `sector`를 기준으로 국내 같은 섹터 peer를 자동 선정한다.
- target 종목과 peer의 최신 시세와 재무 데이터를 불러와 비교 지표를 계산한다.
- LLM 없이도 재현 가능한 `CompetitorResult`를 생성한다.
- Strategist가 기존처럼 `score`, `peer_summary`, `peers`, `evidence`를 사용할 수 있게 호환성을 유지한다.
- 데이터 부족, peer 부족, 결측 지표를 결과에 명시해 Guardrail과 UI가 보수적으로 표시할 수 있게 한다.
- 팀원이 흐름을 검증할 수 있는 실험용 notebook과 PM용 문서를 남긴다.

---

## 3. Non-Goals

- 글로벌 peer 비교는 하지 않는다. MVP는 국내 같은 `company.sector` 중심이다.
- LLM이 새로운 숫자, 추정치, 멀티플을 만들게 하지 않는다.
- Streamlit 화면 구현은 이번 설계의 1차 구현 범위에서 제외한다.
- `analysis_cache`, `analysis_history` 저장은 인터페이스를 염두에 두되 이번 코어 PR에서 필수 구현하지 않는다.
- Quant Agent의 5년 밸류에이션 전체 로직을 Competitor Agent 안으로 가져오지 않는다.

---

## 4. Architecture

```text
AgentState.curator
    |
    v
run_competitor(state)
    |
    v
peer_tool.build_peer_comparison(...)
    |
    +-- company: target and same-sector peer candidates
    +-- stock_price: latest close, market_cap, volume
    +-- financial_statement: recent revenue, operating income, net income, equity, liabilities
    |
    v
CompetitorResult
    |
    v
Strategist
```

The boundary is intentional:

| Layer | File | Responsibility |
|------|------|----------------|
| Schema | `src/stock_agent/schemas/analysis.py` | Stable result contract for agent, graph, tests, future UI |
| Tool | `src/stock_agent/tools/peer_tool.py` | DB loading, metric calculation, peer ranking, score calculation |
| Agent | `src/stock_agent/agents/competitor.py` | Validate upstream state, call peer tool, convert tool output into `CompetitorResult` |
| Prompt | `src/stock_agent/prompts/competitor/system.md` | Future LLM explanation rules; MVP works without it |
| Tests | `tests/agents/test_competitor.py`, `tests/tools/test_peer_tool.py` | Calculation and result contract checks |
| Notebook | `notebooks/competitor_agent_walkthrough.ipynb` | PM/developer walkthrough using sample or DB-backed execution |
| PM Docs | `docs/agents/competitor_agent_mvp.md`, `docs/agents/competitor_agent_mvp.html` | What was built, how to validate, remaining work |

---

## 5. Component Design

### 5.1 Schema

`CompetitorResult` remains backward compatible with current fields:

- `score`
- `peer_summary`
- `peers`
- `evidence`

It should be extended with optional fields that match A3:

- `peer_selection_summary`
- `metric_definitions`
- `relative_position`
- `data_quality_flags`
- `a1_peer_multiple_payload`
- `warnings`

Backward compatibility matters because `streamlit_app.py`, `pipeline.py`, and `run_strategist` already consume the simple fields.

### 5.2 Tool

`peer_tool.py` should provide small functions rather than one opaque function.

Recommended functions:

- `load_target_company(conn, stock_code)`
- `load_peer_candidates(conn, target, max_peer_count)`
- `load_latest_prices(conn, stock_codes)`
- `load_financial_snapshots(conn, corp_codes, lookback_years)`
- `calculate_peer_metrics(company_rows, price_rows, financial_rows)`
- `rank_peer_metrics(metric_rows, target_stock_code)`
- `build_peer_comparison(conn, stock_code, sector=None, min_peer_count=3, max_peer_count=8, lookback_years=3)`

The tool should return typed Pydantic models defined in `peer_tool.py`. The agent then converts that tool model into `CompetitorResult`.

### 5.3 Agent

`run_competitor(state)` should:

1. Require `state.curator`.
2. Use the curator target stock code and sector.
3. Call the peer tool.
4. Convert tool output into `CompetitorResult`.
5. Fall back to the current demo-like mock only when DB access is unavailable in Phase 1 demo mode, and mark that fallback with a warning.

The fallback should not silently look like live data.

### 5.4 Prompt

`src/stock_agent/prompts/competitor/system.md` will define future LLM behavior:

- Use only tool-provided values.
- Do not invent peer names, market caps, PER, PBR, ROE, or growth rates.
- Explain peer selection criteria.
- Lower confidence when peer count or data completeness is weak.
- Avoid investment advice wording.

The GIC v11 prompt can be used only as inspiration for structure: peer mapping criteria, CSV/table discipline, verification tags, and source/date awareness. It should not be copied as-is because this project uses DB-backed structured outputs, not chatbot web-search reports.

---

## 6. Metrics And Scoring

Minimum metric set:

| Metric | Direction | Calculation Source |
|------|-----------|--------------------|
| PER | lower is generally cheaper, except negative earnings become not applicable | latest market cap / latest net income |
| PBR | lower is generally cheaper, except missing equity becomes not applicable | latest market cap / latest equity |
| ROE | higher is stronger | latest net income / latest equity |
| Revenue growth | higher is stronger | latest revenue versus previous comparable year |
| Operating margin | higher is stronger | latest operating income / latest revenue |
| Debt ratio | lower is safer | latest liabilities / latest equity |

Score policy:

- Compute metric-level percentile/rank within target plus selected peers.
- Use conservative defaults when metrics are missing.
- Penalize peer count below 3.
- Penalize target data completeness below the minimum usable threshold.
- Return a 0-100 `score`, where 50 is neutral peer position.

The MVP formula is:

```text
score =
  20% valuation_position
+ 25% profitability_position
+ 20% growth_position
+ 15% margin_position
+ 10% balance_sheet_position
+ 10% data_quality
```

If fewer than three reliable metrics exist for the target, return a low-confidence neutral score and a data quality warning instead of forcing a strong conclusion.

---

## 7. Data Flow

Input:

- `stock_code`
- optional `corp_code`
- optional `sector`
- `min_peer_count=3`
- `max_peer_count=8`
- `lookback_years=3`

DB reads:

- `company`: target and same-sector peer candidates
- `stock_price`: latest price, market cap, volume
- `financial_statement`: recent revenue, operating income, net income, equity, liabilities

Output:

- `CompetitorResult.score`
- `CompetitorResult.peer_summary`
- `CompetitorResult.peers`
- `CompetitorResult.evidence`
- optional detail fields for future UI/A1 integration

---

## 8. Error Handling

| Situation | Behavior |
|-----------|----------|
| `state.curator` is missing | Raise `ValueError`; graph ordering is wrong |
| Target company not found | Agent returns `CompetitorResult(score=0, peer_summary=...)` with `target_not_found` warning |
| Target sector missing | Return result with low score, no auto peer extraction, and `sector_missing` warning |
| Peer candidates are fewer than 3 | Continue with available peers, lower score confidence, add `peer_count_below_minimum` |
| Price data missing | Exclude PER/PBR and market-cap ranking for affected company, add warning |
| Financial data missing | Exclude affected metrics; if target lacks core financials, return insufficient data result |
| Negative or zero denominator | Mark metric `not_applicable`; do not impute |
| DB connection unavailable | In demo mode only, use explicit mock fallback with `mock_data_fallback` warning |

---

## 9. Testing Strategy

Unit tests should avoid requiring a live DB.

Test cases:

- Same-sector peer selection excludes the target stock.
- Peer ranking prefers market-cap proximity and data completeness.
- PER/PBR/ROE/growth/margin calculations are deterministic.
- Negative earnings produce `not_applicable` PER.
- Peer count below 3 returns a warning and lower confidence.
- `run_competitor` still produces fields consumed by current Strategist.
- Phase 1 pipeline test continues to pass.

If DB-backed integration tests are added, they should be optional and skipped unless `DATABASE_URL` is available.

---

## 10. Notebook And Docs

The notebook should be a walkthrough, not the production source of truth.

Notebook sections:

1. Load sample target.
2. Show candidate peers.
3. Show raw latest price and financial rows.
4. Show calculated metric table.
5. Show final `CompetitorResult`.
6. Explain warnings and next implementation steps.

PM document sections:

- What Competitor Agent now does.
- Which DB tables it uses.
- How peer selection works.
- How to interpret score and warnings.
- What is intentionally excluded from MVP.
- How UI can render this later.

---

## 11. Implementation Order

1. Extend schema while keeping existing fields compatible.
2. Build pure metric calculation helpers in `peer_tool.py`.
3. Add tests for helper calculations.
4. Add DB loading helpers.
5. Update `run_competitor` to use the tool and explicit fallback.
6. Add agent-level tests.
7. Add prompt markdown.
8. Add notebook walkthrough.
9. Add PM docs.
10. Run tests and lint where available.

---

## 12. Approval Notes

The user approved the practical recommendation on 2026-05-26:

- Build the MVP 실사용형 Competitor Agent.
- Prefer the professional core-first path.
- Defer Streamlit UI to the next PR unless the implementation reveals a very small, low-risk UI hook.

---

## 13. Self-Review

- Placeholder scan: none found.
- Consistency check: the design keeps UI out of the first PR while still preparing UI-ready fields.
- Scope check: the first implementation is a single focused Competitor Agent core PR, not a broad multi-agent rewrite.
- Ambiguity check: global peer, LLM-generated numbers, and cache persistence are explicitly out of scope for this MVP PR.
