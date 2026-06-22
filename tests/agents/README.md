# `tests/agents/` - Agent 동작 검증

> 전문 Agent의 점수·근거·폴백과 Guardrail 통합 계약을 검증합니다.

## 핵심 범위

- Quant, Qual, Competitor, Macro, Strategist의 정상·데이터 부족 경로
- Investment pipeline과 Guardrail 통합
- Competitor LLM 보강과 규칙 기반 비교
- 외부 DB·네트워크 대신 monkeypatch와 결정적 fixture 사용
- 실패 시 보수적 결과와 warning 유지 여부 확인

## 기술 스택과 동작

pytest가 각 `run_*` 함수를 Pydantic `AgentState`로 호출하고 결과 모델의 점수 범위, 근거, 상태 플래그를 검증합니다.

## 실행

```bash
python -m pytest tests/agents -v
```

## 구조

`test_<agent>_agent.py`는 개별 Agent, `test_pipeline_guardrail_integration.py`는 합성 이후 안전 검증을 담당합니다. `macro_README.md`는 Macro 테스트 전용 참고 문서입니다.
