# `prompts/competitor/` - Competitor 프롬프트

> Tool이 계산한 peer 비교를 근거 보존형 설명으로 변환하는 `system.md`를 보관합니다.

수치를 새로 만들지 않고 상대 위치, 결측, 품질 flag를 해석해야 합니다. 프롬프트 변경 후 `python -m pytest tests/agents/test_competitor_llm.py`와 `python eval/run_competitor_eval.py`를 실행합니다.

[프롬프트 인덱스](../README.md)
