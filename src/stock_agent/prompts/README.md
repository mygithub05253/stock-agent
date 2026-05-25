# `src/stock_agent/prompts/` — LLM 프롬프트 분리 보관

## 왜 코드와 분리하나요

- **비개발자도 수정 가능** — PM·기획자가 프롬프트만 손볼 수 있어야 합니다.
- **A/B 테스트 용이** — 같은 에이전트의 프롬프트를 v1/v2 비교 실험.
- **버전 관리** — Git diff로 프롬프트 변화 추적.

## 파일 규칙

```
prompts/
├── curator/
│   ├── system.md              ← 시스템 프롬프트
│   └── output_schema.md       ← 구조화 출력 지시
├── quant/
│   ├── system.md
│   └── explanation.md
├── qual/
│   ├── system.md
│   └── rag_summary.md
├── competitor/
├── strategist/
│   ├── system.md
│   ├── self_critique.md
│   └── tier_output.md
└── guardrail/
    ├── system.md
    └── finance_policy.md
```

## 작성 가이드

1. **시스템 프롬프트는 .md** — 줄바꿈·강조·표가 보존돼야 함
2. **Few-shot 예시는 .json** — 코드에서 동적으로 N개 선택해 삽입
3. **변경 시 평가 하네스 재실행** — `eval/run_benchmark.py` 로 점수 회귀 확인
4. **모르면 모른다고 지시** — 출처 없는 추정이나 숫자 생성을 금지
5. **구조화 출력 고정** — agent output은 Pydantic schema와 맞아야 함
6. **금융 표현 제한** — “수익 보장”, “무조건 매수”, “확실한 수익” 등은 금지
7. **분석 신호 표현** — BUY/HOLD/SELL은 투자 권유가 아니라 데이터 기반 분석 신호로 표현

## Agent별 핵심 prompt 조건

| Agent | 핵심 조건 |
|-------|-----------|
| Curator | 종목을 임의 확정하지 말고 후보를 반환 |
| Quant | 계산값을 새로 만들지 말고 Tool 계산 결과만 해석 |
| Qual | 검색된 RAG chunk에 없는 사실은 말하지 않음 |
| Competitor | peer 선정 기준과 결측 여부를 명시 |
| Strategist | signal과 portfolio suitability를 분리 |
| Guardrail | 위험 표현을 완화하거나 `passed=false` 반환 |
