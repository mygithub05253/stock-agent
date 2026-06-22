# ADR-005: 11노드 LangGraph StateGraph 전환

| 항목 | 값 |
|------|-----|
| 작성자 | PM (코드 정합 기반) |
| 작성일 | 2026-06-20 |
| 상태 | **Accepted** — 코드에 이미 반영됨(`graph/pipeline.py:404-435`) |
| 영향 범위 | `src/stock_agent/graph/pipeline.py`, `src/stock_agent/agents/` |
| 대체 대상 | [ADR-003](ADR-003-six-agent-structure.md) (6 에이전트 구조) |
| 관련 ADR | ADR-002 (Critic 분리/통합) |
| 기준 코드(SSOT) | [`pipeline_11node_groundtruth.md`](../architecture/pipeline_11node_groundtruth.md) |

---

## 0. 한 줄 결론

> **에이전트 구조를 6개 동기 순차 → 11노드 LangGraph `StateGraph`로 재작성.** classifier가 `worker_plan`을 결정하고 Send API로 워커를 동적 병렬 fan-out, strategist에서 join. guardrail_apply에 PII 차단 + recomposer revision loop(≤2) 포함.

---

## 1. 배경

ADR-003은 비용·발표 명료성을 이유로 6 에이전트(동기 순차 호출)를 택했다. 이후 강사 재검토에서 **항목1(Multi-Agent 구조)·항목3(sLLM)·항목10(스트리밍)**이 "선언/순차"에 머물러 저평가됐고(32/70 D), 차별화를 위해 LangGraph 기반 실동작 구조로 재작성했다(48/70 C).

---

## 2. 결정 (Decision)

**11노드 `StateGraph`로 전환** (`build_analysis_graph()`):

| # | 노드 | ADR-003 대비 |
|---|------|------|
| 1 | curator | 유지 |
| 2 | **classifier (RequestClassifier)** | 신설 — intent·scope·depth + worker_plan 라우팅 |
| 3 | quant | 유지 |
| 4 | qual | 유지 |
| 5 | competitor | 유지 |
| 6 | **macro** | ADR-003에서 Quant에 흡수 → **조건부 워커 노드로 분리** |
| 7 | strategist | 유지(join·가중 합성) |
| 8 | **investment_analyst** | 신설 — sLLM(qwen-2.5-7b) 최종 보정 |
| 9 | guardrail | 유지(7게이트) |
| 10 | **guardrail_apply** | 신설 — PII 차단 + recomposer revision loop(≤2) |
| 11 | **renderer (ResultRenderer)** | 신설 — Tier 1/2/3 렌더 |

핵심 메커니즘:
- **Send API 동적 fan-out**(`_fanout_workers`): worker_plan에 있는 워커만 병렬 실행. macro는 `scope∈{portfolio,sector}` 또는 `single_stock+섹터확인`일 때만 포함.
- **워커 격리**(`_safe_worker_node`): 한 워커 실패가 전체로 전파되지 않음.
- **revision loop**: guardrail이 `needs_revision`이면 recomposer→strategist→investment_analyst→guardrail 최대 2회 재생성.

---

## 3. 결정 근거

1. **차별화 실증**: StateGraph 컴파일·11 pytest·MCP round-trip으로 [D] 검증돼 "선언만"이 아님이 증명됨(강사 항목1 2→4).
2. **장애 대응**: 워커 try/except 격리 + conservative fallback + 3단 폴백으로 프로덕션급 에러핸들링(항목2 4점).
3. **sLLM 충족**: investment_analyst가 오픈웨이트 qwen-2.5-7b 실호출(항목3 (a)).
4. **노드 점진 스트리밍**: `graph.stream` 노드 단위 yield로 UI 점진 갱신(항목10 1→3).

---

## 4. 결과

### 긍정적
- ✅ 강사 등급 D→C (32→48/70), 핵심 차별축 5개 실동작 전환
- ✅ macro 가시성 회복(독립 노드), Critic 통합 편향을 investment_analyst 보정으로 완화

### 트레이드오프
- ⚠️ 노드 수 증가로 발표 도식 복잡 → 정본 다이어그램([`canonical_diagrams.md`](../architecture/canonical_diagrams.md) §1)으로 가독성 보완
- ⚠️ LLM 호출 증가 → 비용 정책(ADR-004, 월 5만원) 모니터링 필요

---

## 5. 후속 작업

- [x] `multi_agent_architecture.md`·`system_flow.md`·`agent_design.md` 11노드 정합
- [x] ADR-003 superseded 표기
- [ ] `multi_agent_architecture_review.html` Mermaid 11노드 교체(시각자료 인덱스 참조)
- [ ] Supervisor 역할 노드 명시(강사 항목1 4→5 잔여)

---

## 6. 변경 이력

| 날짜 | 버전 | 상태 | 변경 |
|------|------|------|------|
| 2026-06-20 | v1.0 | Accepted | 6 에이전트 → 11노드 LangGraph 전환 결정 문서화(코드 사후 정합), ADR-003 대체 |
