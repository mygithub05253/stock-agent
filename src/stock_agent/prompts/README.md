# `src/stock_agent/prompts/` — LLM 프롬프트 분리 보관

## 왜 코드와 분리하나요

- **비개발자도 수정 가능** — PM·기획자가 프롬프트만 손볼 수 있어야 합니다.
- **A/B 테스트 용이** — 같은 에이전트의 프롬프트를 v1/v2 비교 실험.
- **버전 관리** — Git diff로 프롬프트 변화 추적.

## 파일 규칙

```
prompts/
├── curator/
│   ├── system_v1.md           ← 시스템 프롬프트
│   └── few_shot_examples.json ← 예시 모음
├── qual_worker/
├── quant_worker/
├── competitor/
├── strategist/
└── guardrail/
```

## 작성 가이드

1. **시스템 프롬프트는 .md** — 줄바꿈·강조·표가 보존돼야 함
2. **Few-shot 예시는 .json** — 코드에서 동적으로 N개 선택해 삽입
3. **변경 시 평가 하네스 재실행** — `eval/run_benchmark.py` 로 점수 회귀 확인
