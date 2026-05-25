# 6 에이전트 상세 설계

| 항목 | 값 |
|------|-----|
| 상태 | 최신 기준 문서로 연결 |
| 기준 문서 | `docs/architecture/multi_agent_architecture.md` |
| 팀 논의용 HTML | `docs/architecture/multi_agent_architecture_review.html` |
| 최종 갱신 | 2026-05-25 |

---

## 안내

6 에이전트 상세 설계의 최신 기준은 `docs/architecture/multi_agent_architecture.md`에 정리되어 있다.

이 문서는 기존 README와 PRD에서 참조하던 `agent_design.md` 경로를 유지하기 위한 진입 문서다. 개발팀은 아래 순서로 확인한다.

1. `docs/architecture/multi_agent_architecture.md`
2. `docs/architecture/system_flow.md`
3. `src/stock_agent/agents/README.md`
4. `src/stock_agent/graph/README.md`
5. `src/stock_agent/schemas/README.md`

## 핵심 요약

| Agent | 책임 | 주요 데이터 |
|-------|------|-------------|
| Curator | 사용자 질문에서 의도와 종목 확정 | `company`, `portfolio` |
| Quant | 재무·시세 기반 정량 계산 | `stock_price`, `financial_statement`, `raw_macro` |
| Qual | 뉴스·공시 RAG 기반 정성 분석 | `rag_documents`, `rag_chunks`, `disclosure_*`, `raw_news` |
| Competitor | 같은 섹터 Peer 선정과 비교 | `company`, `stock_price`, `financial_statement` |
| Strategist | 정량·정성·Peer 결과를 포트폴리오 맥락으로 종합 | agent 결과, `portfolio`, `user_profile` |
| Guardrail | 금융 표현, 근거 부족, PII, 평가 검증 | `evidence_bundle`, policy, logs |

## 변경 이력

| 날짜 | 변경 |
|------|------|
| 2026-05-25 | `multi_agent_architecture.md`로 상세 설계를 이관하고 참조 문서 생성 |
