# `db/` - PostgreSQL 데이터 모델

> 정형 금융 데이터와 pgvector RAG 데이터를 한 PostgreSQL 인스턴스에서 관리하는 스키마 영역입니다.

## 폴더 소개

- **What:** Docker가 최초 실행할 SQL과 데이터 저장 계약을 보관합니다.
- **Why:** 수집기와 Agent가 동일한 테이블·키·인덱스를 사용하도록 SSOT를 제공합니다.
- 원천 데이터, 기업 마스터, 시세, 재무, 공시를 정형 테이블로 관리합니다.
- 뉴스·공시 문서와 임베딩 청크는 pgvector 테이블로 관리합니다.
- 기존 볼륨에는 별도 스키마 적용 스크립트를 사용합니다.

## 기술 스택

| 기술 | 역할 |
|------|------|
| PostgreSQL 16 | 트랜잭션·정형 데이터·JSONB |
| pgvector | `vector(1024)` 임베딩 검색 |
| SQL | 테이블, 인덱스, 제약조건, 코멘트 |
| Docker Compose | 초기 SQL 자동 적용 |

## 동작 원리

`docker compose up -d db`가 새 볼륨을 만들 때 [`init/`](init/README.md)의 SQL을 파일명 순서로 실행합니다. 이미 생성된 볼륨은 자동 재실행되지 않으므로 `python scripts/apply_db_schema.py`를 사용합니다.

## 검증

```bash
docker compose up -d db
python scripts/check_db.py
```

## 디렉토리 구조

```text
db/
`- init/
   |- 001_create_raw_tables.sql
   `- 002_create_rag_pgvector.sql
```
