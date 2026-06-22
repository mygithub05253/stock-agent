# `docs/architecture/` - 시스템 구조와 데이터 흐름

> 시스템, Agent, DB, 백테스트, 사용자 입력 구조의 정확한 설계 원본과 브라우저 시각화를 보관합니다.

## 문서 체계

- Markdown/Mermaid: 리뷰와 변경 이력의 기준
- HTML dashboard: 발표·회의용 상호작용 시각화
- ERD: PostgreSQL 테이블과 관계
- README 이미지: 루트 문서를 위한 요약 시각 자료

## 시작점

| 질문 | 문서 |
|------|------|
| 현재 README 시스템 구조 | [`readme_system_architecture.md`](readme_system_architecture.md) |
| 전체 데이터·사용자 흐름 | [`system_flow.md`](system_flow.md) |
| 멀티 Agent 상세 | [`multi_agent_architecture.md`](multi_agent_architecture.md) |
| DB 관계 | [`erd.md`](erd.md) |
| Intake와 Agent handoff | [`user_intake_agent_handoff.md`](user_intake_agent_handoff.md) |

## 갱신 규칙

코드의 노드·테이블·폴백이 바뀌면 Mermaid 원본을 먼저 갱신한 뒤 HTML·이미지를 맞춥니다. 생성형 이미지는 설명용이며 구조의 SSOT가 아닙니다.

[상위 문서 인덱스](../README.md)
