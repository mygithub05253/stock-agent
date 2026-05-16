# ADR-001: 데이터 아키텍처 — Postgres + pgvector 단일 DB

| 항목 | 값 |
|------|-----|
| 작성자 | PM |
| 작성일 | 2026-05-10 |
| 갱신일 | 2026-05-16 |
| 상태 | **Accepted** |
| 영향 범위 | `docker-compose.yml`, `db/`, `src/stock_agent/db.py`, `src/stock_agent/rag/` |

---

## 0. 한 줄 결론

> **정형 데이터와 RAG용 뉴스·공시 원문/임베딩을 모두 Postgres 한 개에 저장한다. 벡터 검색은 pgvector 확장으로 처리한다.**

Chroma는 삭제하지 않고 향후 교체 가능한 optional backend로 남긴다. MVP 기본 경로는 `Postgres + pgvector`다.

---

## 1. 배경

팀은 데이터베이스를 Postgres 1개로 운영하기로 했다. 따라서 뉴스·공시 RAG까지 별도 Chroma에 분리하면 다음 부담이 생긴다.

| 이슈 | 영향 |
|------|------|
| 저장소 2개 운영 | Docker, 백업, 배포, 장애 대응 복잡도 증가 |
| 메타/본문 동기화 | Postgres ID와 Chroma ID가 어긋날 수 있음 |
| 팀원 병렬 작업 | 데이터팀과 에이전트팀이 서로 다른 DB 규칙을 맞춰야 함 |
| Streamlit 시연 | 로컬/배포 환경에서 서비스 수가 늘어남 |

---

## 2. 결정

**Postgres + pgvector 단일 DB를 채택한다.**

### 2.1 데이터 분류

| 데이터 | 저장소 | 테이블 예시 |
|--------|--------|-------------|
| 사용자/포트폴리오 | Postgres | `users`, `holdings` |
| 종목 기본 정보 | Postgres | `company` |
| 가격/거래 데이터 | Postgres | `stock_price` |
| DART 재무 데이터 | Postgres | `financial_statement` |
| 공시 메타/본문 | Postgres | `disclosure_report`, `disclosure_content`, `rag_documents` |
| 뉴스 원문/청크/임베딩 | Postgres + pgvector | `rag_documents`, `rag_chunks` |
| 매크로 데이터 | Postgres | `raw_macro` |
| LLM/분석 로그 | Postgres + LangSmith | 추후 `analysis_history`, LangSmith trace |

### 2.2 RAG 저장 흐름

```text
뉴스/공시 수집
→ 정제된 원문을 rag_documents 저장
→ 청킹
→ 임베딩 생성
→ rag_chunks.embedding vector(1024) 저장
→ Qual Agent가 pgvector similarity search
```

### 2.3 Chroma의 위치

Chroma는 MVP 기본 경로에서 제외한다. 다만 다음 상황에서는 `src/stock_agent/rag/` 아래에 optional adapter로 추가할 수 있다.

- pgvector 검색 품질/속도가 충분하지 않을 때
- 팀원이 Chroma 기반 RAG 실험을 별도 브랜치에서 빠르게 검증할 때
- 발표 이후 벡터 DB 비교 벤치마크가 필요할 때

---

## 3. 결과

### 3.1 긍정적 결과

- Postgres 하나만 띄우면 정형 데이터와 RAG 데이터가 모두 준비된다.
- 뉴스/공시 출처, 청크, 임베딩, 분석 이력의 JOIN이 단순하다.
- 데이터팀은 하나의 DB 스키마만 보고 적재하면 된다.
- Streamlit 로컬 실행과 Docker Compose 구성이 단순하다.
- LangSmith 도입은 DB 선택과 독립적으로 진행 가능하다.

### 3.2 트레이드오프

- pgvector 확장이 포함된 Postgres 이미지가 필요하다.
- 임베딩 차원 변경 시 `rag_chunks.embedding vector(1024)` 마이그레이션이 필요하다.
- Chroma 튜토리얼 코드를 그대로 복사해서 쓰기는 어렵고, Postgres repository로 감싸야 한다.

### 3.3 리스크 대응

| 리스크 | 대응 |
|--------|------|
| 기존 로컬 볼륨에는 새 SQL이 자동 적용되지 않음 | `python scripts/apply_db_schema.py` 실행 |
| 임베딩 모델 변경 | `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS` 환경변수와 마이그레이션 문서화 |
| pgvector 성능 부족 | Chroma optional adapter 또는 인덱스 튜닝 검토 |

---

## 4. 후속 작업

- [x] `docker-compose.yml` DB 이미지를 `pgvector/pgvector:pg16`으로 변경
- [x] `rag_documents`, `rag_chunks` 스키마 추가
- [x] LangSmith 환경변수 placeholder 추가
- [ ] Qual Worker에서 `pgvector_store.py` 검색 함수 연결
- [ ] 데이터팀 뉴스/공시 적재 코드에서 `rag_documents`/`rag_chunks` 저장 연결
- [ ] LangSmith tracing 모듈 추가

---

## 5. 변경 이력

| 날짜 | 버전 | 상태 | 변경 |
|------|------|------|------|
| 2026-05-10 | v0.1 | Accepted | 초기 Postgres + Chroma 분리안 |
| 2026-05-16 | v0.2 | Accepted | Postgres + pgvector 단일 DB로 변경, Chroma는 optional backend로 보존 |
