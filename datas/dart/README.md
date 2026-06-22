# DART & KRX Data

> OpenDART의 기업·재무·공시와 KRX 시세를 PostgreSQL 분석 테이블로 정규화하는 수집 영역입니다.

## 현재 구현 요약

- **What:** 기업 마스터, 재무제표, 공시 메타·원문, 일별 가격을 수집합니다.
- **Why:** Quant·Qual·Competitor가 공식 원천과 기준일이 있는 데이터를 사용하게 합니다.
- `collector.py`는 기업과 보고서 기본 수집 진입점입니다.
- `collect_prices.py`, `collect_financials.py`, `collect_contents.py`가 책임별 배치를 제공합니다.
- `collect_heavyweights.py`는 시연 대상 주요 기업의 통합 수집 흐름입니다.

| 기술 | 역할 |
|------|------|
| OpenDART REST/XML | 기업코드, 재무, 공시 |
| pykrx | KRX 종목·시세·시가총액 |
| psycopg2, PostgreSQL | 정규화와 멱등 적재 |

```bash
python datas/dart/collector.py
python datas/dart/collect_prices.py
python scripts/check_db.py
```

기업 재무제표, 공시 원문 및 주가 데이터 수집/전처리 작업 공간입니다.
본 파트는 단순한 웹 스크래핑이 아니라, 
금융감독원(DART)의 재무/공시 팩트와 한국거래소(KRX)의 시장 데이터를 결합하여 
장기 투자 판단과 밸류에이션(Valuation)에 활용 가능한 형태로 완벽하게 정규화(Normalization)하는 것을 목표로 합니다.

수집 및 적재된 데이터는 이후:
* Quant Worker Agent
* Qual Worker Agent
* Strategist & Synthesizer Agent
등에서 사용됩니다.

---

### 담당 범위

* 기업 마스터 관리: DART 고유번호(`corp_code`)와 KRX 종목코드(`stock_code`) 이원화 매핑
* KRX 시장 데이터 수집: 일별 주가, 시가총액, 섹터(업종) 정보 수집 및 갱신
* DART 재무제표 수집: 최근 3~4개년 핵심 재무 지표(매출, 영업이익, 순이익, 자산/자본 등) 수집
* DART 주요 공시 수집: 정기보고서 및 수시 주요 경영사항 공시 메타데이터 및 원문 수집
* 데이터 정규화 및 적재: 중복 방지 및 멱등성이 보장된 DB Upsert 로직 구현 (PostgreSQL)
* Quant 지표 전처리: 한글 계정과목의 영문 ID 표준화 및 문자열 금액의 정수형(Int) 변환

---

### 데이터 수집 전략

본 프로젝트는:
* 과거 3~4년 데이터를 기반으로 향후 5년 관점의 장기 투자 판단을 목표로 합니다.
* 수만 개의 비상장사를 무차별적으로 수집하지 않고, 사용자가 선택한 관심 섹터 중심으로 관련 종목 및 산업 뉴스만 선택적으로 수집하는 구조로 설계합니다.
* 연결재무제표(CFS)를 최우선 기준으로 하되, 지주사 분석 등을 위해 별도재무제표(OFS) 데이터도 분리하여 무손실 적재합니다.

**예시 (반도체 섹터 매핑):**

| DART 고유번호 | KRX 종목코드 | 기업명 | 섹터 (Sector) | 주요 제품 (Industry) |
| :--- | :--- | :--- | :--- | :--- |
| 00126380 | 005930 | 삼성전자 | 통신 및 방송 장비 제조업 | 반도체, 스마트폰 등 |
| 00164779 | 000660 | SK하이닉스 | 반도체 제조업 | 메모리 반도체 |

---

### 국내 재무/주가 소스

| 소스 (Source) | 수집 대상 | 수집 방식 | 비고 |
| :--- | :--- | :--- | :--- |
| OpenDART API | 단일회사 주요재무사항 (3~4년치) | REST API (JSON) | 일일 호출 한도(1만 회) 고려하여 배치 설계 |
| OpenDART API | 공시검색 및 보고서 원문 | REST API (JSON, XML) | Qual Worker의 RAG 분석용 텍스트 |
| FinanceDataReader | KRX 상장사 마스터 (섹터 포함) | Python Library | `KRX-DESC` 파라미터 활용 (Sector/Industry) |
| FinanceDataReader | 일별 주가 및 시가총액 | Python Library | 시가총액은 PER/PBR 계산의 핵심 |

---

### 데이터 처리 흐름 (ETL Pipeline)

1. 사용자가 섹터 선택
2. 섹터 기반 종목 universe 생성 (`FinanceDataReader` 활용)
3. 타겟 기업의 DART 3~4개년 재무 데이터 및 공시 수집
4. 계정과목 표준화 및 금액 등 정제 작업
5. 복합 유니크 키 기반 DB 적재 (Upsert)
6. 최신 주가 동기화
7. 이후 Quant 계산 및 RAG 연결

---

### 핵심 스키마 구조 (PostgreSQL)

반정형 텍스트 위주의 뉴스(JSONB)와 달리, Quant 계산의 속도와 정확성을 위해 고도로 정규화된 관계형 데이터베이스 구조를 채택합니다.

* `company`: DART코드와 KRX코드를 연결하는 마스터 테이블
* `stock_price`: 밸류에이션 계산을 위한 일별 주가 및 시가총액 팩트
* `financial_statement`: 분석용 핵심 재무 숫자 (연결/별도, 당기/전기 완벽 분리)
* `disclosure_report` & `disclosure_content`: 공시 메타데이터 및 원본 텍스트


**재무제표(`financial_statement`) 저장 예시:**

```json
{
  "corp_code": "00126380",
  "bsns_year": 2023,
  "reprt_code": "11011",
  "fs_div": "CFS",
  "sj_div": "IS",
  "account_id": "OPERATING_PROFIT",
  "account_nm": "영업이익",
  "thstrm_amount": 6567000000000,
  "frmtrm_amount": 43376000000000,
  "updated_at": "2026-05-13 13:00:00"
}
```

---

### 재무/공시 전처리 규칙

| 전처리 항목 | 설명 |
| :--- | :--- |
| **계정과목 매핑** | 한글명('매출액', '영업이익')을 영문 표준 ID(`REVENUE`, `OPERATING_PROFIT`)로 통일 |
| **금액 타입 변환** | DART API의 문자열 금액에서 쉼표 제거 후 정수형(`Integer/BigInt`) 변환 |
| **결측치(NaN) 방어** | KRX 데이터 수집 시 `Sector`가 누락된 경우 `Industry` 항목을 교차 검증하여 매핑 |
| **종목 코드 규격화** | 종목코드가 정수로 변환되어 앞자리 '0'이 날아가는 현상 방지 (`zfill(6)` 적용) |
| **Upsert (멱등성)** | 동일한 `(기업, 연도, 보고서, 제표, 계정)` 조합이 들어오면 기존 데이터를 Update |

---

### 권장 파일 구성

```text
datas/dart/
├── README.md
├── requirements.txt
├── config.py                 # DB 연결 정보 및 API 키 관리 (환경변수)
├── db_schema.sql             # 5개 핵심 테이블 DDL (최초 세팅용)
├── fetch_krx_master.py       # KRX 상장사 및 섹터 마스터 업데이트 배치
├── fetch_financials.py       # DART 3~4년 치 재무제표 수집 및 정제
├── fetch_prices.py           # KRX 일별 주가 및 시가총액 수집
├── fetch_disclosures.py      # DART 공시 메타데이터 및 원문 수집
└── utils/
    ├── db_manager.py         # PostgreSQL 연결 및 Upsert 공통 모듈
    └── data_cleaner.py       # 금액 변환, 계정 매핑 등 전처리 헬퍼 함수
```

---

### 협업 규칙

* `main` 브랜치 직접 수정 금지
* 개인 브랜치에서 작업 후 PR 생성
* 공통 로직은 PM/에이전트 담당과 협의 후 분리
* 새로운 패키지 설치 시 단톡 공유 필수
* `.env` 및 로컬 데이터는 커밋 금지 (`.gitignore` 등록 확인)
* DART API 호출 로직은 일일 트래픽 한도(10,000회)를 고려하여 반드시 테스트 후 커밋할 것

---

### MVP 목표

**초기 MVP 목표:**

1. 국내 재무/주가 소스 연동 및 수집
2. 타겟 섹터 기반 상장사 마스터(`company`) 구축
3. 과거 3~4년 재무 데이터 DB 무결성 적재 (Upsert)
4. Quant 지표 계산을 위한 최신 주가 동기화
5. 이후 Quant/Qual Agent 연결 가능 구조 확보
