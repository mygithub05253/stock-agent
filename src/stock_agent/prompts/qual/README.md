# `prompts/qual/` - Qual 프롬프트

> 검색된 뉴스·공시 chunk만 사용해 정성 근거와 리스크를 분류하는 `system.md`를 보관합니다.

검색 결과에 없는 사실을 생성하지 않고 근거 부족을 warning으로 표현해야 합니다. 변경 후 `python -m pytest tests/agents/test_qual_agent.py`와 제한된 RAGAS 평가를 실행합니다.

[프롬프트 인덱스](../README.md)
