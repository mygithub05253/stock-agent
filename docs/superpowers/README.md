# `docs/superpowers/` - 설계와 구현 계획 기록

> 큰 변경을 시작하기 전에 합의한 설계와 실행 체크리스트를 날짜별 Markdown으로 보존합니다.

## 구조

```text
superpowers/
|- specs/  # What과 Why, 범위, 제약
`- plans/  # 파일별 구현·검증 단계
```

## 동작 원리

```mermaid
flowchart LR
    I[아이디어] --> S[승인된 spec]
    S --> P[implementation plan]
    P --> C[코드·문서 변경]
    C --> V[검증]
```

완료된 문서는 역사적 결정 기록으로 유지하며 현재 구현과 충돌하면 새 설계에서 차이를 설명합니다.

[상위 문서 인덱스](../README.md)
