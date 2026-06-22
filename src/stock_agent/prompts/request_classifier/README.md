# `prompts/request_classifier/` - 질문 분류 프롬프트

> 질문을 intent, analysis scope, urgency reason, requested depth로 구조화하는 `system.md`를 보관합니다.

허용된 enum 값과 JSON 키를 정확히 지키고 종목 조회나 최종 신호 생성을 수행하지 않습니다. 변경 후 `python -m pytest tests/test_phase1_pipeline.py tests/test_eval_harness.py`를 실행합니다.

[프롬프트 인덱스](../README.md)
