**Guardrail & Evaluator Agent**

Purpose
- Final safety and compliance layer before rendering outputs to users.
- Detects PII, profanity, investment-guarantee language, and evidence insufficiency.

Behavior
- Runs deterministically (no external LLM calls) and is safe to run synchronously.
- If PII or profanity found -> `passed=false`, add warnings and redact/soften.
- If guarantee/absolute claims found -> soften headline ("will" -> "may"), append "[수정됨]".
- If evidence is missing -> add warning but may still pass depending on other checks.

Integration
- Called after `Strategist` in `src/stock_agent/graph/pipeline.py`.
- Wrapped in try/except so guardrail failures do not crash the pipeline; a conservative `GuardrailResult` is attached on error.

Prompt & Policy Examples
- System instruction (agent role):

  너는 금융 도메인의 Guardrail Agent다. 출력물이 투자 권유, 수익 보장, 허위 단정, 출처 없는 주장, 개인정보 노출, 또는 욕설에 해당하는지 검사하고 필요시 문구를 완화하거나 출력을 제한하라.

- Softening examples:
  - "This will double your money" -> "This may increase expected returns [수정됨]"
  - "No risk" -> "Reduced visibility on risk [수정됨]"

What to do next
- (Optional) Expand with language-specific rules and policies in `docs/policies/`.
- (Optional) Add a small dataset of negative/positive examples for unit tests.
