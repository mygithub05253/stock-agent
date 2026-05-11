# News Data

뉴스 데이터 수집 및 전처리 작업 공간입니다.

본 파트는 단순 뉴스 크롤링이 아니라,

```text
국내 금융 뉴스 데이터를 수집하고,
장기 투자 판단에 활용 가능한 형태로 구조화하는 것
```

을 목표로 합니다.

수집된 뉴스 데이터는 이후:

- News/RAG Agent
- Synthesizer Agent
- Portfolio Strategist Agent

등에서 사용됩니다.

---

# 담당 범위

- 국내 금융 뉴스 수집
- 기사 제목 / 본문 / 발행 시각 / 출처 / URL 정리
- 섹터 기반 뉴스 필터링
- 장기 산업 트렌드 뉴스 수집
- 중복 기사 식별 기준 정의
- `raw_news` 테이블 적재
- 뉴스 전처리 및 정규화
- 감성 분석 / 이벤트 유형 분류 확장 준비

---

# 뉴스 데이터 수집 전략

본 프로젝트는:

```text
과거 3~4년 데이터를 기반으로
향후 5년 관점의 장기 투자 판단
```

을 목표로 합니다.

따라서 모든 뉴스를 무차별 수집하지 않고,

```text
사용자가 선택한 관심 섹터 중심으로
관련 종목 및 산업 뉴스만 선택적으로 수집
```

하는 구조로 설계합니다.

예시:

| 섹터 | 대표 종목 |
| --- | --- |
| 반도체 | 삼성전자, SK하이닉스 |
| 금융 | KB금융, 신한지주 |
| 바이오 | 셀트리온, 삼성바이오로직스 |

---

# 국내 뉴스 소스

| 소스 | source 값 | 수집 방식 |
| --- | --- | --- |
| 연합뉴스 | yonhap | RSS |
| 한국경제 | hankyung | RSS |
| 매일경제 | mk | RSS |
| 이데일리 | edaily | RSS |
| 네이버 금융 | naver_finance | HTML |
| 네이버 뉴스 검색 | naver_news | HTML |

초기 구현은 안정적인 RSS 수집부터 진행하고,
이후 네이버 금융 HTML 스크래핑을 추가합니다.

---

# 뉴스 처리 흐름

```text
1. 사용자가 섹터 선택
2. 섹터 기반 종목 universe 생성
3. 뉴스 소스별 기사 수집
4. 종목명/섹터 기반 필터링
5. payload JSON 생성
6. raw_news 테이블 저장
7. 이후 전처리 및 RAG 연결
```

---

# raw_news 스키마 방향

초기 뉴스 데이터는 원본 손실을 줄이기 위해 JSONB 기반으로 저장합니다.

핵심 검색 컬럼은 별도 컬럼으로 관리하고,
원본 전체 데이터는 payload JSONB에 저장합니다.

주요 컬럼:

| 컬럼명 | 설명 |
| --- | --- |
| source | 뉴스 출처 |
| source_name | 출처 이름 |
| source_type | rss / html |
| stock_code | 종목코드 |
| stock_name | 종목명 |
| sector | 섹터 |
| title | 기사 제목 |
| url | 기사 URL |
| publisher | 언론사 |
| published_at | 기사 발행 시각 |
| payload | 원본 JSON 데이터 |

---

# 뉴스 저장 예시

```json
{
  "source": "hankyung",
  "source_name": "한국경제",
  "source_type": "rss",

  "stock_code": "005930",
  "stock_name": "삼성전자",
  "sector": "반도체",

  "title": "삼성전자, AI 반도체 수요 회복 기대",
  "url": "https://example.com/news/123",

  "publisher": "한국경제",
  "published_at": "2026-05-08 09:30:00",

  "event_type": "industry_trend",

  "keywords": [
    "HBM",
    "AI",
    "반도체"
  ]
}
```

---

# 뉴스 전처리 규칙

| 전처리 항목 | 설명 |
| --- | --- |
| 중복 제거 | 동일 URL 또는 제목 제거 |
| 광고 제거 | 리딩방, 급등주 등 제거 |
| HTML 제거 | HTML 태그 제거 |
| 날짜 정규화 | TIMESTAMP 형식 통일 |
| 종목 매핑 | 기사와 종목코드 연결 |
| 섹터 매핑 | 기사와 섹터 연결 |
| 키워드 추출 | 핵심 키워드 추출 |
| 감성 분석 | positive / neutral / negative 분류 |
| 이벤트 분류 | earnings, regulation, industry_trend 등 |

---

# 권장 파일 구성

```text
datas/news/
├── README.md
├── collector.py
├── rss_collector.py
├── naver_collector.py
├── parser.py
├── preprocessor.py
└── providers/
```

수집 소스가 증가할 경우:

```text
datas/news/providers/
```

아래에 source별 수집기를 분리합니다.

예시:

```text
providers/
├── yonhap.py
├── hankyung.py
├── mk.py
└── naver_finance.py
```

---

# 협업 규칙

- `main` 브랜치 직접 수정 금지
- 개인 브랜치에서 작업 후 PR 생성
- 뉴스 관련 코드는 `datas/news/` 아래에서만 작업
- 공통 로직은 PM/에이전트 담당과 협의 후 분리
- 새로운 패키지 설치 시 단톡 공유 필수
- `.env` 및 로컬 데이터는 커밋 금지

---

# MVP 목표

초기 MVP 목표:

```text
1. 국내 뉴스 소스 3개 이상 수집
2. 섹터 기반 뉴스 필터링
3. raw_news payload 생성
4. CSV 또는 DB 저장
5. 이후 RAG Agent 연결 가능 구조 확보
```
