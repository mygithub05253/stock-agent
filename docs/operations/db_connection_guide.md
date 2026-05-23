# DB 연결 가이드

| 항목 | 내용 |
|------|------|
| 목적 | 개인 Supabase, 공용 Supabase, 로컬 Postgres를 코드 변경 없이 전환 |
| 기준 파일 | `.env.example`, `docker-compose.yml`, `src/stock_agent/config.py` |
| 보안 원칙 | 실제 DB URL, API Key, 계정/비밀번호는 `.env`에만 저장하고 Git에 올리지 않는다. |

---

## 1. 연결 우선순위

애플리케이션은 `src/stock_agent/config.py`의 `resolved_database_url` 규칙을 따른다.

| 우선순위 | 설정 | 설명 |
|----------|------|------|
| 1 | `DATABASE_URL` | 값이 있으면 개인/공용 Supabase 또는 외부 Postgres로 바로 연결 |
| 2 | `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | `DATABASE_URL`이 비어 있을 때 로컬 Postgres 연결 문자열 생성 |

---

## 2. 로컬 Postgres 사용

`.env`에 아래처럼 둘 수 있다.

```env
APP_ENV=local
DATABASE_URL=
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=stock_agent
POSTGRES_USER=stock_agent
POSTGRES_PASSWORD=stock_agent
```

Docker Compose의 app 컨테이너는 `DATABASE_URL`이 비어 있으면 기본적으로 내부 `db` 서비스에 연결한다.

```env
DATABASE_URL=postgresql://stock_agent:stock_agent@db:5432/stock_agent
```

---

## 3. Supabase 사용

개인 또는 공용 Supabase를 사용할 때는 `.env`의 `DATABASE_URL`만 교체한다.

```env
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@<region>.pooler.supabase.com:6543/postgres?sslmode=require
```

운영 팁:

| 상황 | 권장 방식 |
|------|-----------|
| 개인 실험 DB | 개인 Supabase URL을 로컬 `.env`에만 저장 |
| 팀 공용 DB | 팀 공용 Supabase URL을 팀 비밀 채널에서 공유하고 `.env`에 저장 |
| PR/문서 업로드 | 실제 URL, 비밀번호, API Key를 절대 포함하지 않음 |
| 연결 문제 | `DATABASE_URL`을 비우면 로컬 Postgres 기본값으로 복귀 |

---

## 4. 예외 처리 기준

| 예외 | 처리 |
|------|------|
| `DATABASE_URL` 오타 | 연결 실패 로그를 확인하고 `.env`만 수정한다. 코드는 변경하지 않는다. |
| Supabase 비밀번호 변경 | `.env`의 `DATABASE_URL`만 갱신한다. |
| 개인 DB와 공용 DB 스키마 차이 | `db/init/` SQL 기준으로 스키마 차이를 맞춘다. |
| Git에 비밀값 노출 | 즉시 키/비밀번호를 폐기하고 Git 이력 정리 절차를 진행한다. |

