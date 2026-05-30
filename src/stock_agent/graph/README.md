# `src/stock_agent/graph/` — LangGraph 오케스트레이션

본 폴더는 6개 에이전트를 **LangGraph StateGraph** 로 연결하는 코드를 담습니다.

현재 Phase 1 구현은 `pipeline.py`에서 mock agent 함수를 순차 호출합니다. 목표 구현은 `Curator`와 `RequestClassifier` 이후 `Quant`, `Qual`, `Competitor`를 병렬 fan-out으로 실행하고 `Strategist`에서 병합하는 supervisor graph입니다.

## 파일

| 파일 | 역할 |
|------|------|
| `pipeline.py` | 현재 Phase 1 pipeline. 목표는 StateGraph 정의 + Conditional Edge + fan-out |
| `state.py` | 후속 예정. `AgentState` Pydantic 모델을 분리할 때 사용 |
| `nodes.py` | 후속 예정. 각 에이전트를 노드 함수로 래핑 |

## 목표 흐름 요약

```
START
→ Input Guardrail
→ Curator
→ [Quant, Qual, Competitor 병렬]
→ Strategist
→ Guardrail
→ Tier 1/2/3 Output
```

자세한 설계는 `docs/architecture/multi_agent_architecture.md` 와 `docs/architecture/system_flow.md` 를 기준으로 합니다.

## A2A 도입 기준

MVP에서는 A2A를 도입하지 않습니다. 현재 repo, Streamlit app, Postgres DB가 하나의 실행 경계 안에 있기 때문에 LangGraph supervisor pattern이 더 단순하고 안전합니다.

A2A는 다음 조건이 생기면 v2에서 검토합니다.

- report agent, backtest agent, notification agent가 별도 서비스로 분리됨
- 외부 팀 또는 외부 vendor agent와 연동해야 함
- agent 간 인증/권한/감사 로그가 필요한 독립 실행 환경이 생김

## 구현 시 주의

- `AgentState`에 `request_id`, `as_of_date`, `data_version`, `evidence_bundle`, `cost_trace`를 추가하는 방향을 우선 검토합니다.
- 병렬 실행 agent는 서로의 결과에 의존하지 않아야 합니다.
- `Strategist`가 병합하기 전까지 `Quant`, `Qual`, `Competitor`는 자기 전문 영역 결과만 작성합니다.
- 부분 실패 시 전체 분석을 중단할지, warning과 함께 partial result로 진행할지 정책을 명시해야 합니다.
