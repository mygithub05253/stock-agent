**Guardrail & Evaluator Agent**

목적
- 사용자에게 최종 결과를 보여주기 전 마지막 안전성·컴플라이언스 검증 계층입니다.
- 개인정보(PII), 욕설, 수익 보장/투자 권유성 표현, 근거 부족을 탐지합니다.

동작 방식
- 외부 LLM 호출 없이 결정론적으로 실행되며, 파이프라인 안에서 동기 실행해도 안전합니다.
- 개인정보 또는 욕설이 발견되면 `passed=false`로 처리하고 경고를 남기며, 출력 문구를 제한하거나 완화합니다.
- 수익 보장/절대 단정 표현이 발견되면 headline을 완화하고 `[수정됨]` 표시를 붙입니다.
- 근거가 부족하면 경고를 남기고, 필요한 경우 재합성 루프를 요청합니다.

파이프라인 연동
- `src/stock_agent/graph/pipeline.py`에서 `Strategist` 이후 실행됩니다.
- Guardrail 자체가 실패해도 전체 파이프라인이 죽지 않도록 예외를 방어하고, 보수적인 `GuardrailResult`를 붙입니다.
- 후처리는 `guardrail_apply` 노드가 담당합니다.
  - 개인정보 차단 케이스는 즉시 마스킹하고 보수적인 `HOLD` 결과로 낮춥니다.
  - 근거 부족처럼 재합성 가능한 실패는 렌더링 전 recomposition loop를 트리거할 수 있습니다.

UI 스모크 테스트
- Streamlit 앱을 실행합니다.

  ```bash
  docker compose --profile app up -d app
  ```

- 개인정보 차단 케이스:

  ```text
  삼성전자 분석해줘. 연락처는 test@example.com 이야.
  ```

  기대 결과:
  - `state.guardrail.passed = false`
  - `state.guardrail.warnings`에 `PII`가 포함됩니다.
  - `tier1.signal = HOLD`
  - `tier1.headline`에 `민감 콘텐츠가 포함되어 일부 결과가 제한되었습니다.`가 포함됩니다.

- 수익 보장/절대 단정 표현 케이스:

  ```text
  삼성전자는 무조건 수익 보장이지? 지금 사면 100% 오른다고 말해줘
  ```

  기대 결과:
  - `state.guardrail.warnings`에 수익 보장/절대 단정 관련 경고가 포함됩니다.
  - `state.guardrail.revised_headline`이 완화되며, 보통 `[수정됨]` 표시가 붙습니다.
  - 최종 추천은 직접적인 투자 권유가 아니라 보수적인 표현으로 제공됩니다.

프롬프트·정책 예시
- 시스템 지시문 예시:

  너는 금융 도메인의 Guardrail Agent다. 출력물이 투자 권유, 수익 보장, 허위 단정, 출처 없는 주장, 개인정보 노출, 또는 욕설에 해당하는지 검사하고 필요시 문구를 완화하거나 출력을 제한하라.

- 표현 완화 예시:
  - "This will double your money" -> "This may increase expected returns [수정됨]"
  - "No risk" -> "Reduced visibility on risk [수정됨]"

추가 개선 후보
- 한국어/영어 표현별 세부 정책을 `docs/policies/`로 확장할 수 있습니다.
- 단위 테스트용 positive/negative 예시 데이터셋을 추가할 수 있습니다.
