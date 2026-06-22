# `docs/decisions/` - Architecture Decision Records

> 중요한 기술·운영 선택의 배경, 대안, 결과를 ADR로 보존합니다.

## 작성 원리

- 구현 결과뿐 아니라 왜 다른 대안을 선택하지 않았는지 기록합니다.
- 번호는 생성 순서를 유지하며 기존 ADR 번호를 재사용하지 않습니다.
- 결정이 바뀌면 기존 문서를 삭제하지 않고 새 ADR에서 대체 관계를 적습니다.
- 현재 코드와 충돌하면 상태를 superseded로 갱신합니다.

## 현재 ADR

| 문서 | 결정 |
|------|------|
| `ADR-001` | PostgreSQL + pgvector 단일 저장 전략 |
| `ADR-002` | Critic 분리와 합성 방식 |
| `ADR-003` | Agent 책임 구조 |
| `ADR-004` | 월 LLM 비용 상한 |

[상위 문서 인덱스](../README.md)
