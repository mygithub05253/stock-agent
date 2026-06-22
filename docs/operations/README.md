# `docs/operations/` - 운영 가이드

> DB 연결, LLM 비용, PM 협업처럼 실행 환경과 팀 운영에 필요한 절차를 보관합니다.

## 문서

| 파일 | 내용 |
|------|------|
| `db_connection_guide.md` | PostgreSQL 연결·점검·장애 확인 |
| `llm_cost_guide.md` | 모델 라우팅과 월 비용 상한 |
| `pm_workflow_guide.md` | PM 검수·브랜치·PR 흐름 |

## 기술과 갱신 원칙

Docker Compose, PostgreSQL, 환경변수, GitHub PR 정책을 다룹니다. 실제 명령이나 환경변수가 바뀌면 `.env.example`, `docker-compose.yml`, 루트 README와 함께 갱신합니다. 비밀값은 예시에도 넣지 않습니다.

[상위 문서 인덱스](../README.md)
