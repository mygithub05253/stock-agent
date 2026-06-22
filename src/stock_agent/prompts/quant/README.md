# `prompts/quant/` - Quant 프롬프트

> Tool이 계산한 재무·가격 지표를 해석하는 `system.md`를 보관합니다.

LLM이 PER, PBR, 성장률 같은 수치를 새로 계산하지 않고 입력된 값과 기준일을 보존해야 합니다. 변경 후 `python -m pytest tests/agents/test_quant_agent.py`를 실행합니다.

[프롬프트 인덱스](../README.md)
