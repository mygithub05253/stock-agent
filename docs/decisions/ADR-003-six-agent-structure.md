# ADR-003: 6 에이전트 구조 (8 → 6 압축)

| 항목 | 값 |
|------|-----|
| 작성자 | PM |
| 작성일 | 2026-05-10 |
| 상태 | ~~Accepted~~ → **Superseded by [ADR-005](ADR-005-eleven-node-langgraph.md)** (2026-06-20, 11노드 LangGraph 전환) |
| 영향 범위 | `src/stock_agent/agents/`, `src/stock_agent/graph/pipeline.py` |
| 선행 ADR | ADR-001 (데이터 B안) |
| 관련 ADR | ADR-002 (Critic 분리/통합), **ADR-005 (11노드 전환, 본 ADR 대체)** |

---

> **⚠️ 이 결정은 [ADR-005](ADR-005-eleven-node-langgraph.md)로 대체되었습니다(2026-06-20).** 현재 구현은 6 에이전트가 아니라 **11노드 LangGraph StateGraph**입니다. 당시의 "비용·발표 명료성" 판단 근거는 기록으로 보존하되, 노드 구성의 현행 기준은 [`pipeline_11node_groundtruth.md`](../architecture/pipeline_11node_groundtruth.md)를 따르세요. 본 ADR의 압축 사상(Macro·Critic 통합)은 이후 LangGraph 재작성에서 Macro=조건부 워커 노드, Critic=Strategist 자체검토+InvestmentAnalyst 보정으로 재배치되었습니다.

---

## 0. 한 줄 결론

> **에이전트 수를 6개로 확정.** Curator / Qual / Quant / Competitor / Strategist / Guardrail.
> Macro·Critic은 별도 에이전트 X — 다른 에이전트 안에 통합.

---

## 1. 배경

PRD v0.5 (이전 버전)에서는 **8 에이전트** 구조 검토:
1. Curator
2. Qual Worker
3. Quant Worker
4. Competitor
5. **Macro Injector** ← 별도
6. Synthesizer
7. **Critic** ← 별도
8. Guardrail

팀원 우려 — *"에이전트가 많을수록 LLM 호출 폭증, 비용 부담"*

---

## 2. 결정 (Decision)

**6 에이전트로 압축:**

| # | 에이전트 | 변경 |
|---|----------|------|
| 1 | Curator | 유지 |
| 2 | Qual Worker ★ | 유지 (W1+W3 핵심) |
| 3 | Quant Worker | 유지 (5y 밸류에이션 + Macro 컨텍스트 흡수) |
| 4 | Competitor | 유지 |
| 5 | Strategist & Synthesizer | 통합 (Synthesizer + Critic 검증 단계 흡수) |
| 6 | Guardrail & Evaluator | 유지 (PII + RAGAS 채점) |

### 흡수된 항목

- **Macro Injector** → Quant Worker 안에 "거시 컨텍스트 주입" 단계로
- **Critic** → Strategist 안에 "5 시각 자체 검토" 단계로 (Phase 1 통합 안. Phase 2에 분리 검토 — `ADR-002` 참고)

---

## 3. 결정 근거

### 3.1 비용 안전

| 항목 | 8 에이전트 | 6 에이전트 |
|------|-----------|-----------|
| 1회 LLM 호출 | ~22회 | ~13회 |
| 1회 비용 | 약 65원 | 약 36원 |
| 12주 1,000회 | 65,000원 | 36,000원 |

→ 5만원 상한 안전.

### 3.2 학습 매핑은 그대로

| 강의 | 에이전트 매핑 |
|------|----------------|
| W1 (Vector·Reranker) | Qual Worker |
| W2 (RAGAS) | Guardrail & Evaluator |
| W3 (ReAct + Tool + Memory) | 모든 에이전트 |
| W4 (Streamlit) | UI 영역 |
| W5 (금융 가이드라인) | Guardrail & Evaluator |

→ 6 에이전트 모두 1개 이상 강의 학습 직접 적용.

### 3.3 발표 명료성

8 에이전트 흐름도는 노드가 너무 많아 청중이 한눈에 따라가기 어려움. 6 에이전트가 *기억하기 쉬운 단위* (정량/정성/경쟁/종합/안전 + 입구).

---

## 4. 결과

### 긍정적
- ✅ 비용 안전
- ✅ 흐름도 명료
- ✅ 학습 매핑 유지
- ✅ Phase 1 일정 안전

### 부정적 / 트레이드오프
- ⚠️ Macro 비중이 Quant 안에 묻혀 가시성 ↓
- ⚠️ Critic 통합 시 자기 방어 편향 가능 (→ ADR-002 Phase 2 분리 옵션)

---

## 5. 대안 검토

| 대안 | 채택 안 함 이유 |
|------|------------------|
| 8 에이전트 (Macro + Critic 분리) | 비용·복잡도 부담. Phase 2에 부분 도입 검토 |
| 4 에이전트 (Quant·Qual·Strategist·Guardrail) | Curator·Competitor 흡수 시 책임 너무 큼 |

---

## 6. 후속 작업

- [x] PRD v0.6 §4.1 에 6 에이전트 명시
- [x] 협업 가이드 README에 6 에이전트 소개
- [ ] `src/stock_agent/agents/` 폴더 6 파일 골격 작성 (7주차)
- [ ] `docs/architecture/agent_design.md` 상세 설계 (7주차)

---

## 7. 변경 이력

| 날짜 | 버전 | 상태 | 변경 |
|------|------|------|------|
| 2026-05-10 | v0.1 | Accepted | 8→6 압축 결정 |
