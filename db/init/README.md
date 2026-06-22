# `db/init/` - DB 초기화 SQL

> PostgreSQL 컨테이너의 새 볼륨에 적용되는 순서 보장 SQL 마이그레이션입니다.

## What / Why

- `001_create_raw_tables.sql`은 원천·기업·가격·재무·공시 테이블을 만듭니다.
- `002_create_rag_pgvector.sql`은 `vector` 확장과 RAG 문서·청크 테이블을 만듭니다.
- `IF NOT EXISTS`를 사용해 반복 적용 가능성을 높입니다.
- 파일명 숫자 접두사가 실행 순서를 고정합니다.
- 수집기나 Agent에서 임의로 스키마를 생성하지 않도록 경계를 분리합니다.

## 기술과 동작

| 기술 | 사용 방식 |
|------|-----------|
| PostgreSQL DDL | 테이블·인덱스·제약·코멘트 |
| JSONB | 원천 payload와 유연한 metadata |
| pgvector | cosine distance 기반 벡터 검색 |

Docker의 `/docker-entrypoint-initdb.d` 규칙에 따라 새 볼륨에서만 자동 실행됩니다.

## 변경 규칙

1. 기존 파일을 파괴적으로 재작성하지 않고 다음 번호 SQL을 추가합니다.
2. 기존 볼륨 적용 경로를 `scripts/apply_db_schema.py`에도 반영합니다.
3. `python scripts/check_db.py`와 관련 테스트로 검증합니다.

## 파일 구조

```text
init/
|- 001_create_raw_tables.sql
`- 002_create_rag_pgvector.sql
```
