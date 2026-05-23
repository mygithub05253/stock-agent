### 정의

국내 주식 투자 판단을 돕는 멀티에이전트 기반 포트폴리오 분석 서비스

사용자가 예를 들어,

```jsx
“내 포트폴리오에서 삼성전자 어떻게 할까?”
```

라고 입력하면, 시스템이 사용자 포트폴리오·재무 데이터·주가 데이터·뉴스/공시·동종업계 비교·매크로 데이터를 종합해서 **분석 신호, 핵심 근거, 리스크, 다음 액션**을 제공합니다.

“투자 추천”보다는 **“데이터 기반 분석 신호”**

1. 전체 흐름

```jsx
사용자 입력 (이전에 유저 데이털를 가지고 있음) 성향 관련 + 자금 출처..
   ↓
Curator Agent
- 의도 파악
- 종목 확정
- 종목 미지정 시 후보 추천
   ↓
Quant / Qual / Competitor 병렬 분석
- Quant: 재무·주가·밸류에이션
- Qual: 뉴스·공시 RAG
- Competitor: 동종업계 비교
   ↓
Strategist Agent
- 모든 분석 결과 종합
- BUY/HOLD/SELL 성격의 분석 신호 생성
- 사용자 포트폴리오 적합도 반영
   ↓
Guardrail Agent
- 과도한 투자권유 표현 차단
- 개인정보/욕설/근거 부족 표현 검증
   ↓
Tier 1 / Tier 2 / Tier 3 출력~
```

LangGraph 흐름은 `Curator → Quant/Qual/Competitor 병렬 → Strategist → Guardrail → Tier 1/2/3 출력` 구조

**3. 사용자에게 보이는 결과 구조**

```jsx
Tier 1: 한 줄 결론
- 분석 신호
- 신뢰도
- 적합도
- 핵심 한 문장

Tier 2: 왜 그런 결론이 나왔는지
- 정량 근거
- 정성 근거
- Peer 비교
- 매크로 영향
- 포트폴리오 적합도

Tier 3: 상세 산출물
- PB 리포트 PDF/DOCX
- 밸류에이션 Excel
- 산업/뉴스 분석 HTML
```

4. 에이전트 구성 방향

LLM Agent
= 의도 파악, 요약, 판단, 설명 생성

Worker Agent
= DB 조회, 계산, 필터링, 지표 산출

```jsx
LLM Agent
= 의도 파악, 요약, 판단, 설명 생성

Worker Agent (함수 API)
= DB 조회, 계산, 필터링, 지표 산출
```

| 에이전트 | 성격 | 핵심 역할 |
| --- | --- | --- |
| Curator Agent | LLM + Rule | 사용자 질문 해석, 종목 확정, 후보 추천 |
| Quant Worker | 계산형 Worker | 재무·주가·밸류에이션 분석 |
| Qual Worker | RAG Agent | 뉴스·공시 기반 호재/악재 분석 |
| Competitor Agent | 조회/계산형 Worker | 동종업계 Peer 비교 |
| Strategist Agent | LLM + Scoring | 최종 분석 신호 종합 |
| Guardrail Agent | Rule + Optional LLM | 위험 표현, 투자권유 표현, 근거 부족 차단 |

## 5. 각 에이전트 책임

### 1) Curator Agent

Curator는 사용자의 질문을 이해하고 **무엇을 분석할지 정하는 에이전트**입니다.

역할:

```
- 자연어 입력에서 종목명 추출
- 종목명 → 종목코드 매핑
- 사용자의 투자 의도 파악
- 종목이 없으면 후보 종목 5~10개 추천
- 사용자 관심 섹터와 포트폴리오 정보 반영
```

종목 미지정 시에는 KOSPI/KOSDAQ universe, 시가총액, 거래대금, 섹터, 최근 뉴스 수, 최근 공시 여부 등을 기준으로 후보를 고르는 구조가 적절합니다.

---

### 2) Quant Worker

Quant는 **정량 분석의 핵심 Worker**입니다.

역할:

```
- DART 재무제표 조회
- 주가/거래량 데이터 조회
- PER, PBR, ROE, 성장률, 변동성 계산
- 밸류에이션 점수 산출
- 정량 근거 요약
```

MVP에서는 5개년 전체를 바로 구현하기보다 **최근 3개년 연간 재무제표 + 최근 4개 분기 실적**부터 시작하는 게 좋습니다. Quant에서 보는 주요 항목은 매출액, 영업이익, 순이익, 자산, 부채, 자본, 현금흐름, ROE, 성장성, 부채비율, FCF 등입니다.

---

### 3) Qual Worker

Qual은 **뉴스/공시 기반 정성 분석 Agent**입니다.

역할:

```
- 뉴스/공시 본문 검색
- 호재/악재 추출
- 이벤트 유형 분류
- RAG 근거 문장 정리
- 출처 기반 요약 생성
```

중요한 점은 뉴스 데이터를 단순히 긍정/부정으로만 나누면 약하다는 것입니다. `실적`, `수주/계약`, `신사업`, `규제/정책`, `소송/리스크`, `M&A`, `지배구조`, `산업 트렌드`, `증권사 리포트`처럼 이벤트 유형으로 나누는 편이 더 설득력 있습니다.

---

### 4) Competitor Agent

Competitor는 **동종업계 비교 담당 Worker**입니다.

역할:

```
- 같은 섹터 Peer 추출
- Peer의 PER, PBR, ROE, 매출성장률 비교
- 대상 기업이 업계 내에서 싼지/비싼지/성장성이 좋은지 판단
- Peer Heatmap 형태로 출력
```

이건 처음부터 글로벌 Peer까지 갈 필요 없습니다.

MVP에서는 `company.sector` 기준으로 국내 Peer 3~5개만 비교해도 충분합니다.

---

### 5) Strategist Agent

Strategist는 **최종 판단을 만드는 종합 에이전트**입니다.

역할:

```
- Curator 결과
- Quant 결과
- Qual 결과
- Competitor 결과
- 사용자 포트폴리오 정보
- 매크로 정보
```

를 종합해서 최종적으로 아래를 만듭니다.

```
- 분석 신호
- 신뢰도
- 핵심 근거 3개
- 주요 리스크 2개
- 사용자 포트폴리오 기준 적합도
- 다음 액션
```

문서상 Strategist는 여러 Worker 결과와 회원 프로필/포트폴리오, 매크로 데이터를 종합하는 역할로 잡혀 있습니다.

---

### 6) Guardrail Agent

Guardrail은 **최종 출력 직전의 품질·안전 관리자**입니다.

역할:

```
- 과도한 수익 보장 표현 차단
- 무조건 매수/매도 표현 완화
- 개인정보 노출 차단
- 욕설/부적절 표현 차단
- RAG 근거 부족 시 경고
- 필요 시 문장 재작성 요청
```

예를 들어,

```
“무조건 매수하세요”
```

가 아니라,

```
“현재 데이터 기준으로는 매수 우위의 분석 신호가 있으나, 최종 판단은 사용자의 책임 하에 이루어져야 합니다.”
```

처럼 바꾸는 역할입니다.

# 6. 데이터 구조

MVP에서 필요한 데이터는 6개입니다.

| 데이터 | 사용 목적 |
| --- | --- |
| 사용자/포트폴리오 | 투자 성향, 보유 비중, 손실 감내도 반영 |
| 종목 기본 정보 | 종목명, 종목코드, 섹터 매핑 |
| 가격/거래 데이터 | 수익률, 변동성, 거래대금, 모멘텀 계산 |
| DART 재무 데이터 | 매출, 이익, 자산, 부채, ROE, FCF 계산 |
| 뉴스/RAG 데이터 | 호재/악재, 이벤트, 정성 근거 생성 |
| 매크로 데이터 | 금리, 환율, 지수, CPI 등 시장 환경 반영 |

Postgres

- 정형 데이터 저장
- company
- financial_data
- disclosure
- stock_price
- users
- holdings
- analysis_history

Chroma

- 비정형 텍스트 저장
- 뉴스 본문
- 공시 본문
- 임베딩 벡터

데이터 베이스 저장소 형태

```jsx
Postgres
- 정형 데이터 저장
- company
- financial_data
- disclosure
- stock_price
- users
- holdings
- analysis_history

Chroma
- 비정형 텍스트 저장
- 뉴스 본문
- 공시 본문
- 임베딩 벡터
```

개발 진행 순서

```jsx
삼성전자 1종목 기준으로
Curator → Quant → Strategist → Guardrail → Tier 1 출력까지 연결
```

범위

```jsx
- AgentState 정의
- 각 에이전트 입출력 Schema 정의
- Curator Mock
- Quant Mock 또는 DB 조회
- Strategist Mock
- Guardrail Rule
- Streamlit Tier 1 카드 출력
```

# 7. 개발 진행 순서

처음부터 모든 기능을 구현하면 복잡해집니다.

따라서 아래 순서로 진행하는 게 맞습니다.

## Phase 1. 1종목 E2E

목표:

```
삼성전자 1종목 기준으로
Curator → Quant → Strategist → Guardrail → Tier 1 출력까지 연결
```

구현 범위:

```
- AgentState 정의
- 각 에이전트 입출력 Schema 정의
- Curator Mock
- Quant Mock 또는 DB 조회
- Strategist Mock
- Guardrail Rule
- Streamlit Tier 1 카드 출력
```

이 단계의 목표는 **정확한 분석 완성도보다 전체 파이프라인이 끝까지 도는 것**입니다.

---

## Phase 2. DB 연결

목표:

```
Mock 데이터를 제거하고 실제 Postgres 데이터를 연결
```

구현 범위:

```
- company 조회
- financial_data 조회
- stock_price 조회
- 사용자 포트폴리오 입력값 연결
- Quant 계산 로직 실제화
```

---

## Phase 3. Qual RAG 연결

목표:

```
뉴스/공시 기반 정성 분석 붙이기
```

구현 범위:

```
- 뉴스 수집
- 중복/광고/불필요 문장 정제
- Chroma 인덱싱
- Hybrid Search
- 이벤트 유형 분류
- 근거 기반 요약
```

---

## Phase 4. Competitor + Macro 연결

목표:

```
동종업계 비교와 거시 환경 반영
```

구현 범위:

```
- 같은 섹터 Peer 추출
- Peer 재무/주가 비교
- 금리/환율/지수 데이터 반영
- Strategist 점수에 가중치 적용
```

---

## Phase 5. 리포트/평가 고도화

목표:

```
결과물을 발표/시연 가능한 수준으로 정리
```

구현 범위:

```
- PDF 리포트
- DOCX 리포트
- Excel 밸류에이션
- RAGAS 평가
- Langfuse 로그
- README/BENCHMARK 정리
```

---

# 8. 팀원 역할 분배안

## 데이터팀

```
- DART 수집
- pykrx 가격/거래 수집
- 뉴스 크롤링
- 매크로 데이터 수집
- Postgres 스키마 적용
- Chroma 인덱싱
```

## 에이전트팀

```
- AgentState 정의
- LangGraph graph.py 작성
- Curator Agent
- Quant Worker
- Qual Worker
- Competitor Agent
- Strategist Agent
- Guardrail Agent
```

## 프론트/서비스팀

```
- Streamlit 홈 화면
- 분석 진행중 화면
- 추천 결과 화면
- 상세 산출물 화면
- Tier 1/2/3 UI
- 다운로드 버튼
```

## PM/문서팀

```
- PRD 정리
- 기능 명세 정리
- 발표 흐름 정리
- README 작성
- Demo Scenario 작성
- 평가용 Golden Set 작성
```

### 고민사항

1. 유저 데이터 어떻게 받지?
    1. 회원가입 기능 필요? (mvp여서 간단하게 목 데이터?)
2. 데이터 형식 잘 맞추기

### 정의

국내 주식 투자 판단을 돕는 멀티에이전트 기반 포트폴리오 분석 서비스

사용자가 예를 들어,

```jsx
“내 포트폴리오에서 삼성전자 어떻게 할까?”
```

라고 입력하면, 시스템이 사용자 포트폴리오·재무 데이터·주가 데이터·뉴스/공시·동종업계 비교·매크로 데이터를 종합해서 **분석 신호, 핵심 근거, 리스크, 다음 액션**을 제공합니다.

“투자 추천”보다는 **“데이터 기반 분석 신호”**

1. 전체 흐름

```jsx
사용자 입력 (이전에 유저 데이털를 가지고 있음) 성향 관련 + 자금 출처..
   ↓
Curator Agent
- 의도 파악
- 종목 확정
- 종목 미지정 시 후보 추천
   ↓
Quant / Qual / Competitor 병렬 분석
- Quant: 재무·주가·밸류에이션
- Qual: 뉴스·공시 RAG
- Competitor: 동종업계 비교
   ↓
Strategist Agent
- 모든 분석 결과 종합
- BUY/HOLD/SELL 성격의 분석 신호 생성
- 사용자 포트폴리오 적합도 반영
   ↓
Guardrail Agent
- 과도한 투자권유 표현 차단
- 개인정보/욕설/근거 부족 표현 검증
   ↓
Tier 1 / Tier 2 / Tier 3 출력~
```

LangGraph 흐름은 `Curator → Quant/Qual/Competitor 병렬 → Strategist → Guardrail → Tier 1/2/3 출력` 구조

**3. 사용자에게 보이는 결과 구조**

```jsx
Tier 1: 한 줄 결론
- 분석 신호
- 신뢰도
- 적합도
- 핵심 한 문장

Tier 2: 왜 그런 결론이 나왔는지
- 정량 근거
- 정성 근거
- Peer 비교
- 매크로 영향
- 포트폴리오 적합도

Tier 3: 상세 산출물
- PB 리포트 PDF/DOCX
- 밸류에이션 Excel
- 산업/뉴스 분석 HTML
```

4. 에이전트 구성 방향

LLM Agent
= 의도 파악, 요약, 판단, 설명 생성

Worker Agent
= DB 조회, 계산, 필터링, 지표 산출

```jsx
LLM Agent
= 의도 파악, 요약, 판단, 설명 생성

Worker Agent (함수 API)
= DB 조회, 계산, 필터링, 지표 산출
```

| 에이전트 | 성격 | 핵심 역할 |
| --- | --- | --- |
| Curator Agent | LLM + Rule | 사용자 질문 해석, 종목 확정, 후보 추천 |
| Quant Worker | 계산형 Worker | 재무·주가·밸류에이션 분석 |
| Qual Worker | RAG Agent | 뉴스·공시 기반 호재/악재 분석 |
| Competitor Agent | 조회/계산형 Worker | 동종업계 Peer 비교 |
| Strategist Agent | LLM + Scoring | 최종 분석 신호 종합 |
| Guardrail Agent | Rule + Optional LLM | 위험 표현, 투자권유 표현, 근거 부족 차단 |

## 5. 각 에이전트 책임

### 1) Curator Agent

Curator는 사용자의 질문을 이해하고 **무엇을 분석할지 정하는 에이전트**입니다.

역할:

```
- 자연어 입력에서 종목명 추출
- 종목명 → 종목코드 매핑
- 사용자의 투자 의도 파악
- 종목이 없으면 후보 종목 5~10개 추천
- 사용자 관심 섹터와 포트폴리오 정보 반영
```

종목 미지정 시에는 KOSPI/KOSDAQ universe, 시가총액, 거래대금, 섹터, 최근 뉴스 수, 최근 공시 여부 등을 기준으로 후보를 고르는 구조가 적절합니다.

---

### 2) Quant Worker

Quant는 **정량 분석의 핵심 Worker**입니다.

역할:

```
- DART 재무제표 조회
- 주가/거래량 데이터 조회
- PER, PBR, ROE, 성장률, 변동성 계산
- 밸류에이션 점수 산출
- 정량 근거 요약
```

MVP에서는 5개년 전체를 바로 구현하기보다 **최근 3개년 연간 재무제표 + 최근 4개 분기 실적**부터 시작하는 게 좋습니다. Quant에서 보는 주요 항목은 매출액, 영업이익, 순이익, 자산, 부채, 자본, 현금흐름, ROE, 성장성, 부채비율, FCF 등입니다.

---

### 3) Qual Worker

Qual은 **뉴스/공시 기반 정성 분석 Agent**입니다.

역할:

```
- 뉴스/공시 본문 검색
- 호재/악재 추출
- 이벤트 유형 분류
- RAG 근거 문장 정리
- 출처 기반 요약 생성
```

중요한 점은 뉴스 데이터를 단순히 긍정/부정으로만 나누면 약하다는 것입니다. `실적`, `수주/계약`, `신사업`, `규제/정책`, `소송/리스크`, `M&A`, `지배구조`, `산업 트렌드`, `증권사 리포트`처럼 이벤트 유형으로 나누는 편이 더 설득력 있습니다.

---

### 4) Competitor Agent

Competitor는 **동종업계 비교 담당 Worker**입니다.

역할:

```
- 같은 섹터 Peer 추출
- Peer의 PER, PBR, ROE, 매출성장률 비교
- 대상 기업이 업계 내에서 싼지/비싼지/성장성이 좋은지 판단
- Peer Heatmap 형태로 출력
```

이건 처음부터 글로벌 Peer까지 갈 필요 없습니다.

MVP에서는 `company.sector` 기준으로 국내 Peer 3~5개만 비교해도 충분합니다.

---

### 5) Strategist Agent

Strategist는 **최종 판단을 만드는 종합 에이전트**입니다.

역할:

```
- Curator 결과
- Quant 결과
- Qual 결과
- Competitor 결과
- 사용자 포트폴리오 정보
- 매크로 정보
```

를 종합해서 최종적으로 아래를 만듭니다.

```
- 분석 신호
- 신뢰도
- 핵심 근거 3개
- 주요 리스크 2개
- 사용자 포트폴리오 기준 적합도
- 다음 액션
```

문서상 Strategist는 여러 Worker 결과와 회원 프로필/포트폴리오, 매크로 데이터를 종합하는 역할로 잡혀 있습니다.

---

### 6) Guardrail Agent

Guardrail은 **최종 출력 직전의 품질·안전 관리자**입니다.

역할:

```
- 과도한 수익 보장 표현 차단
- 무조건 매수/매도 표현 완화
- 개인정보 노출 차단
- 욕설/부적절 표현 차단
- RAG 근거 부족 시 경고
- 필요 시 문장 재작성 요청
```

예를 들어,

```
“무조건 매수하세요”
```

가 아니라,

```
“현재 데이터 기준으로는 매수 우위의 분석 신호가 있으나, 최종 판단은 사용자의 책임 하에 이루어져야 합니다.”
```

처럼 바꾸는 역할입니다.

# 6. 데이터 구조

MVP에서 필요한 데이터는 6개입니다.

| 데이터 | 사용 목적 |
| --- | --- |
| 사용자/포트폴리오 | 투자 성향, 보유 비중, 손실 감내도 반영 |
| 종목 기본 정보 | 종목명, 종목코드, 섹터 매핑 |
| 가격/거래 데이터 | 수익률, 변동성, 거래대금, 모멘텀 계산 |
| DART 재무 데이터 | 매출, 이익, 자산, 부채, ROE, FCF 계산 |
| 뉴스/RAG 데이터 | 호재/악재, 이벤트, 정성 근거 생성 |
| 매크로 데이터 | 금리, 환율, 지수, CPI 등 시장 환경 반영 |

Postgres

- 정형 데이터 저장
- company
- financial_data
- disclosure
- stock_price
- users
- holdings
- analysis_history

Chroma

- 비정형 텍스트 저장
- 뉴스 본문
- 공시 본문
- 임베딩 벡터

데이터 베이스 저장소 형태

```jsx
Postgres
- 정형 데이터 저장
- company
- financial_data
- disclosure
- stock_price
- users
- holdings
- analysis_history

Chroma
- 비정형 텍스트 저장
- 뉴스 본문
- 공시 본문
- 임베딩 벡터
```

개발 진행 순서

```jsx
삼성전자 1종목 기준으로
Curator → Quant → Strategist → Guardrail → Tier 1 출력까지 연결
```

범위

```jsx
- AgentState 정의
- 각 에이전트 입출력 Schema 정의
- Curator Mock
- Quant Mock 또는 DB 조회
- Strategist Mock
- Guardrail Rule
- Streamlit Tier 1 카드 출력
```

# 7. 개발 진행 순서

처음부터 모든 기능을 구현하면 복잡해집니다.

따라서 아래 순서로 진행하는 게 맞습니다.

## Phase 1. 1종목 E2E

목표:

```
삼성전자 1종목 기준으로
Curator → Quant → Strategist → Guardrail → Tier 1 출력까지 연결
```

구현 범위:

```
- AgentState 정의
- 각 에이전트 입출력 Schema 정의
- Curator Mock
- Quant Mock 또는 DB 조회
- Strategist Mock
- Guardrail Rule
- Streamlit Tier 1 카드 출력
```

이 단계의 목표는 **정확한 분석 완성도보다 전체 파이프라인이 끝까지 도는 것**입니다.

---

## Phase 2. DB 연결

목표:

```
Mock 데이터를 제거하고 실제 Postgres 데이터를 연결
```

구현 범위:

```
- company 조회
- financial_data 조회
- stock_price 조회
- 사용자 포트폴리오 입력값 연결
- Quant 계산 로직 실제화
```

---

## Phase 3. Qual RAG 연결

목표:

```
뉴스/공시 기반 정성 분석 붙이기
```

구현 범위:

```
- 뉴스 수집
- 중복/광고/불필요 문장 정제
- Chroma 인덱싱
- Hybrid Search
- 이벤트 유형 분류
- 근거 기반 요약
```

---

## Phase 4. Competitor + Macro 연결

목표:

```
동종업계 비교와 거시 환경 반영
```

구현 범위:

```
- 같은 섹터 Peer 추출
- Peer 재무/주가 비교
- 금리/환율/지수 데이터 반영
- Strategist 점수에 가중치 적용
```

---

## Phase 5. 리포트/평가 고도화

목표:

```
결과물을 발표/시연 가능한 수준으로 정리
```

구현 범위:

```
- PDF 리포트
- DOCX 리포트
- Excel 밸류에이션
- RAGAS 평가
- Langfuse 로그
- README/BENCHMARK 정리
```

---

# 8. 팀원 역할 분배안

## 데이터팀

```
- DART 수집
- pykrx 가격/거래 수집
- 뉴스 크롤링
- 매크로 데이터 수집
- Postgres 스키마 적용
- Chroma 인덱싱
```

## 에이전트팀

```
- AgentState 정의
- LangGraph graph.py 작성
- Curator Agent
- Quant Worker
- Qual Worker
- Competitor Agent
- Strategist Agent
- Guardrail Agent
```

## 프론트/서비스팀

```
- Streamlit 홈 화면
- 분석 진행중 화면
- 추천 결과 화면
- 상세 산출물 화면
- Tier 1/2/3 UI
- 다운로드 버튼
```

## PM/문서팀

```
- PRD 정리
- 기능 명세 정리
- 발표 흐름 정리
- README 작성
- Demo Scenario 작성
- 평가용 Golden Set 작성
```

### 고민사항

1. 유저 데이터 어떻게 받지?
    1. 회원가입 기능 필요? (mvp여서 간단하게 목 데이터?)
2. 데이터 형식 잘 맞추기