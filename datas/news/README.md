# News Data Pipeline & Semantic Retrieval

기업 뉴스, 산업 이슈, 거시경제 기사 및 공시 기반 텍스트 데이터를 수집·정제·검색 가능한 형태로 구조화하는 작업 공간입니다.

본 파트는 단순 뉴스 크롤링이 아니라:

* 금융 뉴스 데이터 수집
* 정성(Qualitative) 정보 구조화
* RAG(Retrieval-Augmented Generation)
* AI 기반 투자 분석
* 백테스트(Backtesting) 기반 예측 검증

을 위한 전체 뉴스 데이터 파이프라인 구축을 목표로 합니다.

현재 프로젝트는:

* MVP 시연 가능한 구조
* 이후 실제 서비스 확장이 가능한 구조

를 동시에 고려하여 설계합니다.

---

# 프로젝트 목표

본 프로젝트의 목표는:

```text
뉴스 + 공시 + 시장 데이터를 기반으로
AI가 특정 종목에 대한 투자 의견을 생성하고,
백테스트 기반으로 해당 판단의 신빙성을 검증할 수 있는
금융 AI 분석 환경을 구축하는 것
```

입니다.

---

# 현재 MVP 목표

현재 MVP 단계에서는:

* 최근 뉴스 기반 RAG 구축
* 뉴스 Retrieval 기반 AI 투자 분석
* Streamlit 시연 환경 구축
* 백테스트(Time Masking) 기반 예측 검증
* PostgreSQL(pgvector) 기반 Semantic Search

를 우선 구현합니다.

즉:

```text
"완벽한 금융 플랫폼"
```

보다,

```text
"실제로 동작하는 AI 투자 분석 데모"
```

를 우선 목표로 합니다.

---

# 장기 확장 목표 (Phase 2+)

향후에는:

* 장기 뉴스 아카이브 구축
* 글로벌 뉴스 확장
* 멀티 에이전트 기반 금융 분석
* 장기 투자 맥락(Context) 분석
* 실시간 이벤트 탐지
* 뉴스 기반 이상 탐지(Event Spike Detection)
* 고급 감성 분석
* 벡터DB 다중 백엔드 구성

등으로 확장합니다.

---

# 담당 범위

## 뉴스 데이터 수집

* 국내외 금융/경제 뉴스 수집
* 산업·섹터 기반 뉴스 파이프라인 구축
* 종목 기반 뉴스 Retrieval
* 기업·섹터·매크로 뉴스 연결

---

## 뉴스 데이터 전처리

* HTML 제거
* 본문 정제
* 기사 중복 제거
* 날짜 표준화
* 종목 태깅
* 이벤트(Event Type) 분류
* 감성(Sentiment) 전처리

---

## RAG 및 Semantic Retrieval

* 뉴스 기반 Semantic Search
* pgvector 기반 Vector Retrieval
* 향후 Chroma 확장 지원
* 날짜 기반 Retrieval 제어
* 백테스트용 Time Masking 지원

---

## Streamlit 시연 연결

* 뉴스 Retrieval 결과 출력
* AI 투자 의견 출력
* 백테스트 결과 비교
* 실제 주가와 AI 예측 비교

---

# 현재 데이터 수집 전략 (MVP)

현재 MVP 단계에서는:

* 최근 6개월 데이터 우선
* 네이버 금융 중심
* 종목 기반 Retrieval
* 빠른 시연 가능한 구조
* 최소한의 안정적인 데이터 흐름

을 우선합니다.

즉:

```text
"거대한 장기 뉴스 플랫폼"
```

보다,

```text
"최근 뉴스 기반 AI 분석 흐름"
```

구축을 우선합니다.

---

# 장기 데이터 수집 전략 (Phase 2+)

향후에는:

* 과거 3~5년 뉴스 흐름 분석
* 장기 산업 Context 구축
* 글로벌 뉴스 통합
* 경쟁사 뉴스 연결
* 산업 트렌드 장기 추적

등으로 확장합니다.

---

# 뉴스 소스

## 현재 MVP

| 소스      | 수집 대상     | 방식       | 비고        |
| ------- | --------- | -------- | --------- |
| 네이버 금융  | 종목 뉴스     | Crawling | MVP 핵심    |
| DART 공시 | 기업 공시     | API      | 공시 기반 RAG |
| ECOS    | 금리/환율/CPI | API      | 매크로 컨텍스트  |

---

## 향후 확장

| 소스            | 수집 대상     |
| ------------- | --------- |
| 한국경제          | 산업/기업 뉴스  |
| 매일경제          | 시장/거시 뉴스  |
| 연합뉴스          | 정책/속보 뉴스  |
| Reuters       | 글로벌 기업 뉴스 |
| Yahoo Finance | 미국 증시 뉴스  |
| Investing.com | 글로벌 매크로   |

---

# 데이터 처리 흐름 (ETL Pipeline)

## 현재 MVP 흐름

```text
1. company 기반 종목 선택
2. 최근 뉴스 수집
3. 기사 제목/요약 추출
4. HTML 제거 및 정제
5. 이벤트 타입 분류
6. 감성 점수 계산
7. PostgreSQL 저장
8. RAG 검색용 문서 저장
9. Streamlit 출력
10. AI 분석 연결
```

---

## 향후 확장 흐름

```text
뉴스 전문 수집
→ chunking
→ embedding 생성
→ Vector DB 저장
→ Semantic Retrieval
→ Multi-Agent 분석
→ 장기 투자 Context 생성
```

---

# Time Masking & Backtesting

본 프로젝트는:

```text
미래 데이터 누수(Data Leakage)
```

를 방지하기 위해 Time Masking 기반 백테스트 구조를 적용합니다.

예시:

```text
AI 기준 현재 시점:
2026-05-21 23:59

AI 입력 데이터:
2026-05-15 ~ 2026-05-21

예측 대상:
2026-05-22
```

즉:

* AI는 cutoff_date 이후 데이터를 절대 볼 수 없음
* 뉴스 Retrieval도 cutoff_date 기준 제한
* 실제 결과는 발표 시점에서 비교 가능

이를 통해:

```text
AI 분석의 신빙성을 직관적으로 검증
```

할 수 있습니다.

---

# Retrieval 제어 정책

모든 뉴스 Retrieval은:

```sql
published_at <= cutoff_date
```

조건을 만족해야 합니다.

즉:

* 미래 뉴스 Retrieval 금지
* 미래 공시 Retrieval 금지
* 미래 주가 Retrieval 금지

를 보장해야 합니다.

---

# PostgreSQL 저장 구조

## raw_news

원천 뉴스 payload 저장용 테이블

| 컬럼명          | 설명      |
| ------------ | ------- |
| source       | 뉴스 출처   |
| external_id  | 뉴스 식별자  |
| title        | 기사 제목   |
| published_at | 발행 시각   |
| payload      | 원본 JSON |
| collected_at | 수집 시각   |

---

## rag_documents

RAG 검색용 문서 저장 테이블

| 컬럼명          | 설명              |
| ------------ | --------------- |
| source_type  | news/disclosure |
| source       | 뉴스 출처           |
| external_id  | 뉴스 식별자          |
| corp_code    | 기업 코드           |
| stock_code   | 종목 코드           |
| title        | 기사 제목           |
| url          | 기사 URL          |
| published_at | 발행 시각           |
| content      | 검색용 본문          |
| content_hash | 중복 제거 해시        |
| metadata     | 이벤트/감성 JSON     |

---

# Vector DB 전략

## 현재 MVP

현재 MVP 단계에서는:

```text
Supabase(PostgreSQL + pgvector)
```

단일 구조를 우선 사용합니다.

이유:

* 시연 안정성 확보
* 빠른 개발 속도
* DB 관리 단순화
* Retrieval 구조 통합

---

## 향후 확장

향후:

* Chroma
* 별도 Vector DB
* Hybrid Retrieval
* Multi-Backend Retrieval

등으로 확장 가능합니다.

---

# 뉴스 전처리 규칙

| 항목       | 설명                          |
| -------- | --------------------------- |
| HTML 제거  | 광고/스크립트 제거                  |
| 본문 정제    | 기자 정보 제거                    |
| 공백 정리    | 줄바꿈 및 공백 정리                 |
| 기사 중복 제거 | 제목/URL/hash 기반              |
| 날짜 표준화   | UTC/KST 통일                  |
| 종목 태깅    | 기업명 → stock_code            |
| 이벤트 분류   | earnings/regulation/macro 등 |
| 감성 분석    | -1.0 ~ 1.0 점수               |
| 날짜 필터링   | cutoff_date 이후 차단           |

---

# 이벤트 타입 기준

| event_type     | 의미     |
| -------------- | ------ |
| earnings       | 실적/매출  |
| regulation     | 규제/정책  |
| contract       | 수주/계약  |
| mna            | 인수합병   |
| industry_trend | 산업 트렌드 |
| macro          | 거시경제   |
| risk           | 악재/리스크 |
| general        | 일반 뉴스  |

---

# 권장 파일 구조

```text
datas/news/
├── README.md
├── collector.py
├── preprocess_news.py
├── embed_news.py
├── save_to_pgvector.py
├── save_to_chroma.py
└── utils/
    ├── text_cleaner.py
    ├── deduplicator.py
    ├── event_classifier.py
    ├── sentiment.py
    ├── embedding_manager.py
    └── ticker_mapper.py
```

---

# collector.py 역할

collector.py는:

* company 기반 뉴스 수집
* 뉴스 메타데이터 정제
* raw_news 저장
* rag_documents 저장
* 날짜 기반 Retrieval 지원

을 담당합니다.

현재 MVP 기준:

* 최근 6개월
* 네이버 금융 중심
* 제목/요약 기반 Retrieval
* Time Masking 지원

까지 우선 구현합니다.

---

# Streamlit 시연 목표

최종 시연 흐름:

```text
종목 선택
→ 최근 뉴스 Retrieval
→ AI 투자 의견 생성
→ 실제 다음날 주가 비교
→ 백테스트 검증
```

예시:

```text
"HBM 수요 증가 및 외국인 순매수 흐름을 기반으로
삼성전자 단기 상승 가능성이 높다고 판단합니다."
```

→ 실제 다음날 상승 결과 표시

---

# 협업 규칙

* main 브랜치 직접 수정 금지
* 개인 브랜치에서 작업 후 PR 생성
* API 키는 반드시 .env 사용
* .env 및 캐시 데이터 커밋 금지
* robots.txt 및 요청 빈도 준수
* 뉴스 원문 무단 재배포 금지
* 데이터 범위 변경 시 PM 공유 필수
* Retrieval 정책 변경 시 Agent 담당과 협의

---

# 현재 최우선 목표

현재 가장 중요한 목표는:

```text
완벽한 장기 투자 플랫폼 구축
```

이 아니라,

```text
뉴스 기반 AI 분석 + 백테스트 검증이
실제로 동작하는 MVP 시연 환경 구축
```

입니다.

즉:

* 안정적인 뉴스 Retrieval
* Time Masking 기반 검증
* Streamlit 시연 가능 흐름
* AI 투자 의견 생성

을 우선합니다.
