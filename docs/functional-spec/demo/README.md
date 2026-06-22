# `docs/functional-spec/demo/` - 시연 검증 기능 명세

> 실제 미래를 기다리지 않고 기준일 이후 데이터를 마스킹해 분석 흐름을 검증하는 데모 계약입니다.

## 파일과 동작

`D1_backtesting_validation_spec_v0.1.md`가 타깃 예측일, 입력 데이터 마스킹, 1·2·4주 검증 단위와 출력 조건을 정의합니다.

```mermaid
flowchart LR
    D[타깃 날짜] --> M[이후 데이터 마스킹]
    M --> A[Agent 분석]
    A --> C[실제 결과 대조]
```

상세 구조는 [`docs/architecture/backtesting_demo_architecture.md`](../../architecture/backtesting_demo_architecture.md)를 참고합니다.

[기능 명세 인덱스](../README.md)
