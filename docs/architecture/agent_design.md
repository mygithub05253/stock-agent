# 11노드 에이전트 상세 설계

| 항목 | 값 |
|------|-----|
| 상태 | 최신 기준 문서로 연결 |
| 기준 코드(SSOT) | [`docs/architecture/pipeline_11node_groundtruth.md`](pipeline_11node_groundtruth.md) |
| 기준 문서 | `docs/architecture/multi_agent_architecture.md` |
| 팀 논의용 HTML | `docs/architecture/multi_agent_architecture_review.html` |
| 최종 갱신 | 2026-06-20 (6→11노드 정합) |

---

## 안내

11노드 에이전트 상세 설계의 최신 기준은 `docs/architecture/multi_agent_architecture.md`에 정리되어 있다(구 6 에이전트 → 11노드, ADR-005).

이 문서는 기존 README와 PRD에서 참조하던 `agent_design.md` 경로를 유지하기 위한 진입 문서다. 개발팀은 아래 순서로 확인한다.

1. `docs/architecture/multi_agent_architecture.md`
2. `docs/architecture/system_flow.md`
3. `src/stock_agent/agents/README.md`
4. `src/stock_agent/graph/README.md`
5. `src/stock_agent/schemas/README.md`

## 핵심 요약

| # | 노드 | 책임 | 주요 데이터 |
|---|------|------|-------------|
| 1 | Curator | 사용자 질문에서 의도와 종목 확정 | `company`, `portfolio` |
| 2 | RequestClassifier | intent·scope·depth 분류 + worker_plan 결정 | `user_query`, `curator` |
| 3 | Quant | 재무·시세 기반 정량 계산 | `stock_price`, `financial_statement`, `raw_macro` |
| 4 | Qual | 뉴스·공시 RAG 기반 정성 분석 | `rag_documents`, `rag_chunks`, `raw_news` |
| 5 | Competitor | 같은 섹터 Peer 선정과 비교 (DB→MCP→mock) | `company`, MCP `market_metrics` |
| 6 | Macro | 거시경제 환경 분석 (조건부) | `raw_macro`, ECOS |
| 7 | Strategist | 워커 결과를 포트폴리오 맥락으로 join·합성 | 워커 결과, `portfolio`, `user_profile` |
| 8 | InvestmentAnalyst | sLLM(qwen-2.5-7b) 최종 신호·문장 보정 | `strategist` |
| 9 | Guardrail | 금융 표현·근거·PII·평가 7게이트 검증 | `strategist`, policy |
| 10 | Guardrail Apply | PII 차단 + recomposer revision loop(≤2) | `strategist`, `guardrail` |
| 11 | ResultRenderer | Tier 1/2/3 렌더 | state 전체 |

> 구 6 에이전트 대비 신설/분리: RequestClassifier·Macro·InvestmentAnalyst·Guardrail Apply·ResultRenderer. 상세 입출력 계약은 [`interface_spec.md`](../interface/interface_spec.md), 결정 근거는 [`ADR-005`](../decisions/ADR-005-eleven-node-langgraph.md).

## 변경 이력

| 날짜 | 변경 |
|------|------|
| 2026-05-25 | `multi_agent_architecture.md`로 상세 설계를 이관하고 참조 문서 생성 |
