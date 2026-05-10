# `src/stock_agent/graph/` — LangGraph 오케스트레이션

본 폴더는 6개 에이전트를 **LangGraph StateGraph** 로 연결하는 코드를 담습니다.

## 파일

| 파일 | 역할 |
|------|------|
| `pipeline.py` | StateGraph 정의 + Conditional Edge + Send API fan-out |
| `state.py` | `AgentState` Pydantic 모델 (모든 노드가 공유하는 상태) |
| `nodes.py` | 각 에이전트를 노드 함수로 래핑 |

## 흐름 요약 (자세히는 `docs/architecture/system_flow.md`)

```
START → Curator → [Quant, Qual+Competitor 병렬] → Strategist → Guardrail → END
```

## A2A (Agent-to-Agent) 패턴 — 10주차 도입 예정

10주차에 Strategist ↔ Critic 사이에 메시지 프로토콜을 명시적으로 정의합니다. 자세한 ADR은 `docs/decisions/ADR-005-a2a-pattern.md` 참조 (작성 예정).
