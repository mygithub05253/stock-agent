# `prompts/investment_analyst/` - InvestmentAnalyst 프롬프트

> 전문 Agent 근거와 사용자 적합도를 최종 분석 문장으로 보정하는 `system.md`를 보관합니다.

입력 수치와 signal을 보존하고 투자 권유·수익 보장 표현을 만들지 않아야 합니다. 외부 모델 실패 시 기존 Strategist 결과가 fallback으로 유지됩니다.

변경 후 `python -m pytest tests/test_phase1_pipeline.py tests/agents/test_guardrail_agent.py`를 실행합니다.

[프롬프트 인덱스](../README.md)
