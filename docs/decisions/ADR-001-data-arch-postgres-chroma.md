# ADR-001: 데이터 아키텍처 — Postgres + Chroma 분리 (B안)

| 항목 | 값 |
|------|-----|
| 작성자 | PM |
| 작성일 | 2026-05-10 |
| 상태 | **Accepted** (사용자 결정 — 2026-05-09) |
| 영향 범위 | `db/`, `src/stock_agent/db.py`, `src/stock_agent/rag/` |

---

## 0. 한 줄 결론

> **정형 데이터(회원·재무·시세) = Postgres. 비정형 데이터(뉴스·공시 본문 + 임베딩) = Chroma. 두 DB를 분리해 운영한다.**

---

## 1. 배경 (Context)

뉴스·공시 같은 텍스트 데이터를 어디에 저장할지 4가지 옵션이 있었음:

| 옵션 | 구조 | 비고 |
|------|------|------|
| A | Postgres에 텍스트도 저장 (BYTEA 임베딩) | 벡터 검색 불가 → W1 학습 무력 |
| **B** ⭐ | Postgres + Chroma 분리 | 표준 패턴 |
| C | Postgres + pgvector 단일 | DB 1개로 통일, Supabase 친화 |
| D | Postgres + Chroma + S3 (객체 스토리지) | 엔터프라이즈 패턴, 오버엔지니어링 |

---

## 2. 결정 (Decision)

**B 안 채택** — Postgres + Chroma 분리.

### 2.1 결정 근거

1. **부트캠프 W1·W3 실습에서 Chroma 사용** → 팀원 학습 곡선 ↓
2. **로컬 Postgres 각자 설치** (사용자 결정) — Supabase 의존성 없음
3. **Chroma는 Docker 또는 로컬 폴더로 가벼움** — 별도 서버 불필요
4. **명확한 책임 분리** — DB 두 개를 보면 "어디에 뭐가 있는지" 직관적

### 2.2 데이터 분류

| 데이터 | 저장소 | 이유 |
|--------|--------|------|
| 회원 (`users`) | Postgres | JOIN·트랜잭션·인증 |
| 보유 종목 (`holdings`) | Postgres | 회원 FK |
| 종목 기본 (`company`) | Postgres | DART corp_code 기반 |
| 5y 재무 (`financial_data`) | Postgres | 시계열 집계 |
| 시세 (`stock_price`) | Postgres | 시계열 집계 |
| 공시 메타 (`disclosure`) | Postgres | DART 메타 |
| 매크로 시계열 | Postgres | 시계열 집계 |
| 분석 이력 (`analysis_history`) | Postgres | 회원 JOIN |
| **뉴스 본문 + 임베딩** | **Chroma** | 벡터 유사도 검색 |
| **공시 본문 + 임베딩** | **Chroma** | 벡터 유사도 검색 |

### 2.3 동기화 전략

뉴스를 수집하면:
1. 메타(URL·날짜·제목)는 Postgres 또는 정형 테이블에 저장
2. 본문은 Chroma에 청크 + 임베딩으로 저장
3. **공통 키**: 뉴스 ID (UUID) — 양쪽 모두 같은 ID로 식별

---

## 3. 결과 (Consequences)

### 3.1 긍정적 결과

- ✅ W1 학습 (Hybrid Search + Reranker) 그대로 적용
- ✅ Chroma는 가벼워서 Streamlit Cloud 1GB 제약 안에서 충분
- ✅ Postgres 백업·마이그레이션이 단순 (정형 데이터만)
- ✅ 비정형 데이터(임베딩) 변경 시 Chroma만 리빌드 — Postgres 영향 X

### 3.2 부정적 결과 / 트레이드오프

- ⚠️ DB 2개 운영 = 백업·연결 관리 부담 ↑ (단, Chroma는 파일 기반이라 백업 단순)
- ⚠️ 두 DB 동기화 깨질 위험 (뉴스 ID 매칭 누락) → 데이터 적재 시 트랜잭션 처리 필수
- ⚠️ 분석 이력에서 인용 출처 추적 시 두 DB JOIN 불가 → 애플리케이션 코드에서 결합

### 3.3 리스크 대응

| 리스크 | 대응 |
|--------|------|
| Chroma 데이터 손실 | 매일 백업 자동화 (`scripts/backup_chroma.py`) |
| 두 DB 동기화 실패 | 적재 스크립트에 트랜잭션 wrapper + 실패 시 롤백 |
| 임베딩 모델 변경 시 마이그레이션 | Chroma 컬렉션을 `news_chunks_v1`, `v2` 로 버전 관리 |

---

## 4. 대안 비교 (참고용)

| 옵션 | 채택 안 함 이유 |
|------|------------------|
| A (Postgres only) | 벡터 검색 불가 → 부트캠프 W1 학습 무력화 |
| C (Postgres + pgvector) | 사용자가 로컬 Postgres 결정 — pgvector 확장 설치 추가 부담 |
| D (Postgres + Chroma + S3) | MVP 12주 일정 대비 오버엔지니어링 |

---

## 5. 후속 작업

- [ ] `docker-compose.yml` 에 Chroma 서비스 추가 (또는 로컬 파일 기반)
- [ ] `src/stock_agent/rag/chroma_store.py` 구현
- [ ] 데이터팀이 뉴스 적재 시 Postgres + Chroma 동시 트랜잭션 패턴 확립

---

## 6. 변경 이력

| 날짜 | 버전 | 상태 | 변경 |
|------|------|------|------|
| 2026-05-10 | v0.1 | Accepted | 사용자 결정 (2026-05-09) 기록 |
