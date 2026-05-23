# 기능 명세서 v0.8 - A2. 산업·정성 분석

| 항목 | 값 |
|------|-----|
| 작성자 | PM |
| 작성일 | 2026-05-23 |
| 버전 | v0.8 |
| 상위 문서 | `docs/prd/PRD_v0.6.md` |
| 참조 문서 | `docs/functional-spec/overview/functional_spec_all_features_v0.1.md`, `docs/functional-spec/basic/B4_stock_basic_info_spec_v0.6.md`, `docs/functional-spec/advanced/A1_valuation_5y_spec_v0.7.md`, `docs/architecture/system_flow.md`, `docs/architecture/erd.md`, `docs/operations/llm_cost_guide.md` |
| 대상 사용자 | 개인투자자, PM, 개발팀, 데이터팀 |
| 기능 ID | `A2` |
| 기능명 | 산업·정성 분석 |

---

## 0. 문서 메타 정보

본 문서는 PRD 기준 고급 기능 `A2. 산업·정성 분석`의 상세 기능 명세서다. 기존 통합 초안의 7대 표준 양식인 **트리거 / 전제조건 / 입력 / 처리 흐름 / 출력 / 예외 처리 / 담당** 순서를 유지하고, Qual Worker가 뉴스·공시·산업 컨텍스트를 RAG로 분석하는 흐름을 구체화한다.

`A2`는 정량 수치만으로 설명하기 어려운 산업 변화, 사업 구조, 뉴스 이벤트, 공시 리스크를 근거 기반으로 요약하는 기능이다. 모든 핵심 문장에는 출처를 연결해야 하며, LLM은 검색된 근거 안에서만 요약하도록 제한한다. 월 LLM 비용 5만원 상한 정책을 지키기 위해 24시간 분석 캐시, 검색 결과 재사용, 임계점별 호출 축소, 템플릿 대체 응답을 포함한다.

---

## 1. 문서 위치 / 작성 원칙

| 원칙 | 적용 방식 |
|------|-----------|
| Markdown 콘텐츠와 HTML 대시보드 분리 | 본 문서는 기능 명세 Markdown이며, 산업·뉴스 발표 대시보드는 별도 HTML로 관리한다. |
| 프롬프트와 코드 분리 | 뉴스/공시 요약 프롬프트와 이벤트 분류 프롬프트는 코드에 직접 삽입하지 않고 문서 또는 프롬프트 폴더에 격리한다. |
| 기능별 파일 분리 | `A2` 단일 기능만 다루며 A1 밸류에이션, A3 Peer 비교, A4 권유 판단은 결과 연계만 명시한다. |
| 7대 표준 양식 준수 | 트리거, 전제조건, 입력, 처리 흐름, 출력, 예외 처리, 담당을 고정 순서로 작성한다. |
| 출처 기반 생성 | LLM 답변은 `rag_documents`, `rag_chunks`, `disclosure`에서 검색된 근거를 벗어나지 않는다. |
| 비용 상한 명시 | A2 1회 실행당 LLM 호출은 최대 3회, 월 LLM 비용은 5만원 상한 내에서 제어한다. |
| MVP 범위 명확화 | MVP는 최근 뉴스·공시 기반의 정성 요약과 호재/악재 분류를 우선 제공한다. |

---

## 2. 기능 개요

산업·정성 분석 기능은 사용자가 특정 종목의 사업 환경과 최근 이슈를 빠르게 이해하도록 돕는 기능이다. B4 종목 기본 정보 화면 또는 A4 통합 분석 플로우에서 호출되며, Qual Worker가 뉴스 본문, DART 공시, 산업 키워드, 기업 메타 정보를 검색해 근거 있는 정성 리포트를 생성한다.

MVP 화면은 산업 요약, 사업 구조, 최근 뉴스 타임라인, 호재/악재 이벤트 분류, 공시 핵심 리스크, ESG/규제 키워드, 출처 목록으로 구성한다. LLM은 새로운 사실을 추정하지 않고 검색된 근거를 요약·분류·정렬하는 역할만 수행한다.

---

## 3. 핵심 요약 표

| 항목 | 내용 |
|------|------|
| 기능명 | 산업·정성 분석 |
| 기능 ID | `A2` |
| 목적 | 뉴스·공시·산업 맥락을 근거 기반으로 요약해 투자 판단의 정성 근거 제공 |
| 주요 사용자 | B4에서 종목 상세를 확인한 사용자, A4 종합 판단을 요청한 사용자 |
| 주 트리거 | B4의 `이 종목 분석하기`, A4 통합 분석 플로우의 Qual Worker 호출 |
| 전제조건 | `company`, `rag_documents`, `rag_chunks`, `disclosure` 데이터 적재 및 pgvector 검색 가능 |
| 주요 입력 | `stock_code`, `user_id`, `analysis_window_days`, `top_k`, 뉴스/공시 청크 |
| 메인 에이전트 | Qual Worker |
| 보조 에이전트 | Strategist, Guardrail, Evaluator, Report Worker |
| 주요 DB | `company`, `rag_documents`, `rag_chunks`, `disclosure`, `analysis_cache`, `analysis_history` |
| 주요 출력 | 산업 요약, 뉴스 타임라인, 호재/악재 분류, 공시 리스크, 출처 인용, `QualReport` |
| LLM 비용 정책 | 24시간 내 동일 종목 A2 결과 캐시 우선, 캐시 미스 시 최대 3회 |
| 월 비용 상한 | 전체 서비스 월 LLM 비용 50,000원 초과 방지 |
| 품질 기준 | RAGAS Faithfulness 0.80 이상, 출처 없는 핵심 주장 0건 |
| MVP 범위 | 최근 30~90일 뉴스와 최신 사업보고서/분기보고서 기반 정성 요약 |
| 제외 범위 | 최종 BUY/HOLD/SELL 권유, 재무 밸류에이션 계산, 경쟁사 정량 비교 |

---

## 4. A2. 산업·정성 분석

### 4.1 트리거

- 사용자가 B4 종목 기본 정보 화면에서 `이 종목 분석하기` 버튼을 클릭한다.
- 사용자가 A1 밸류에이션 결과 화면에서 `정성 근거 보기`를 클릭한다.
- 사용자가 B5 포트폴리오 일괄 안내 결과에서 특정 종목의 `뉴스·공시 근거 보기`를 클릭한다.
- 사용자가 A4 BUY/HOLD/SELL 권유 플로우에 진입했고, LangGraph가 정성 분석 선행 작업으로 A2를 호출한다.
- 사용자가 기존 정성 분석 이력에서 `최신 뉴스로 다시 분석`을 클릭한다.

### 4.2 전제조건

| 조건 | 상세 |
|------|------|
| 종목 코드 확정 | `stock_code`는 6자리 문자열이며 `company` 테이블에 존재해야 한다. |
| 기업 메타 적재 | `company`에 종목명, 시장구분, 산업분류, DART 고유번호가 있어야 한다. |
| 뉴스 데이터 적재 | `rag_documents`와 `rag_chunks`에 최근 뉴스 본문, 제목, 출처, 발행일이 적재되어 있어야 한다. |
| 공시 데이터 적재 | DART 사업보고서/분기보고서 메타는 `disclosure`에, 원문 청크는 `rag_chunks`에 연결되어 있어야 한다. |
| pgvector 검색 가능 | `rag_chunks.embedding` 기반 벡터 검색과 키워드 검색을 함께 사용할 수 있어야 한다. |
| Sanitizer 통과 | 크롤링 본문은 중복 제거, 광고/저작권 불필요 문구 제거, HTML 태그 제거를 통과해야 한다. |
| 비용 상태 확인 | 월 LLM 비용 집계가 5만원 상한을 초과하지 않아야 한다. 임계점 접근 시 호출 수를 축소한다. |
| 캐시 조회 가능 | 동일 종목·동일 분석 기간·동일 데이터 기준의 최근 24시간 A2 결과를 조회할 수 있어야 한다. |

### 4.3 입력

| 필드 | 타입 | 필수 | 출처 | 설명 |
|------|------|------|------|------|
| `stock_code` | string | Y | B4/B5/A4 | 분석 대상 종목 코드. 6자리 숫자 문자열 |
| `user_id` | string/null | N | 세션 | 분석 이력 저장 및 개인화 연결용 사용자 ID |
| `analysis_window_days` | integer | N | UI/기본값 | 뉴스 검색 기간. 기본 90일, 빠른 분석은 30일 |
| `top_k_news` | integer | N | 시스템 기본값 | 뉴스 RAG 검색 상위 문서 수. 기본 10건 |
| `top_k_disclosure` | integer | N | 시스템 기본값 | 공시 RAG 검색 상위 청크 수. 기본 8건 |
| `include_disclosure` | boolean | N | UI/기본값 | 공시 분석 포함 여부. 기본 `true` |
| `include_esg_regulation` | boolean | N | UI/기본값 | ESG/규제 키워드 포함 여부. 기본 `true` |
| `force_refresh` | boolean | N | UI | 24시간 캐시를 무시하고 재분석할지 여부 |
| `company_profile` | object | Y | `company` | 종목명, 산업, 시장, DART 고유번호 |
| `news_chunks` | array | N | `rag_chunks` | 뉴스 본문 청크와 임베딩 검색 결과 |
| `disclosure_chunks` | array | N | `rag_chunks`/`disclosure` | 공시 원문 청크와 메타 |
| `cost_state` | object | Y | 운영 집계 | 당월 LLM 사용액, 임계점 상태 |

### 4.4 처리 흐름

1. **요청 검증**
   - `stock_code` 형식이 6자리 숫자 문자열인지 확인한다.
   - `company` 테이블에서 종목명, 산업분류, 시장구분, DART 고유번호를 조회한다.
   - 종목이 없으면 A2 분석을 시작하지 않고 B3 검색으로 복귀할 수 있는 예외 응답을 반환한다.

2. **월 LLM 비용 상태 확인**
   - 운영 비용 집계에서 당월 LLM 사용액을 조회한다.
   - 30,000원 이상이면 검색 문서 수와 요약 길이를 축소한다.
   - 40,000원 이상이면 LLM 호출을 1회로 축소하고 뉴스/공시 통합 요약만 생성한다.
   - 50,000원 이상이면 신규 LLM 호출을 중지하고 규칙 기반 템플릿 요약과 원문 링크만 제공한다.

3. **24시간 분석 캐시 우선 조회**
   - `analysis_cache` 또는 `analysis_history`에서 `feature_id = A2`, `stock_code`, `analysis_window_days`, `data_version`, `retrieval_hash`가 같은 최근 24시간 결과를 조회한다.
   - 캐시가 있고 `force_refresh = false`이면 RAG 검색과 LLM 호출을 생략한다.
   - 캐시된 `QualReport`를 UI에 즉시 반환하고 `최근 정성 분석 재사용` 배지를 표시한다.

4. **뉴스 RAG 후보 검색**
   - `rag_documents`에서 `stock_code`, 기업명, 산업 키워드, 최근 기간 조건으로 후보 문서를 필터링한다.
   - `rag_chunks`에서 키워드 검색과 pgvector 벡터 검색을 결합한 Hybrid Search를 수행한다.
   - 중복 기사, 동일 본문 재전송 기사, 광고성 콘텐츠는 제거한다.
   - 검색 결과에는 제목, 출처, 발행일, URL, 청크 ID, 유사도 점수를 포함한다.

5. **공시 RAG 후보 검색**
   - `include_disclosure = true`이면 `disclosure`에서 최신 사업보고서, 반기보고서, 분기보고서를 조회한다.
   - 사업의 내용, 주요 제품/서비스, 위험요인, 연구개발, 소송/우발채무, 특수관계자 거래 관련 청크를 우선 검색한다.
   - DART 공시가 없으면 공시 분석 섹션만 제외하고 뉴스 중심 정성 분석을 계속한다.

6. **근거 컨텍스트 압축**
   - 검색된 청크를 출처별·날짜별·이벤트 유형별로 정렬한다.
   - LLM 입력 토큰이 과도해지지 않도록 중복 문장과 낮은 점수 청크를 제거한다.
   - 각 청크에는 `source_id`, `published_at`, `url`, `chunk_id`를 유지해 후속 인용이 가능하게 한다.

7. **뉴스 이벤트 분류**
   - LLM 또는 규칙 기반 분류기로 최근 뉴스를 9개 이벤트 유형으로 분류한다.
   - 이벤트 유형은 `실적`, `수주`, `신사업`, `규제`, `소송`, `M&A`, `경영진`, `산업`, `증권사 리포트`로 고정한다.
   - 각 이벤트는 `positive`, `negative`, `neutral`, `mixed` 감성 라벨과 신뢰도를 가진다.
   - 비용 임계점이 높으면 LLM 분류 대신 키워드 기반 1차 분류만 제공한다.

8. **산업·사업 구조 요약 생성**
   - Qual Worker가 산업 구조, 매출 동인, 주요 고객/제품, 경쟁 환경, 경기 민감도를 요약한다.
   - 모든 핵심 문장에는 근거 청크 ID 또는 출처 URL을 연결한다.
   - 근거가 없는 내용은 `확인된 근거 없음`으로 표시하고 생성하지 않는다.

9. **공시 리스크 요약 생성**
   - 공시 청크를 기반으로 사업보고서의 주요 리스크, 소송/규제, 원재료 가격, 환율, 고객 집중도, 연구개발 방향을 요약한다.
   - 공시 본문이 오래되었거나 최신 분기보고서가 없으면 기준일을 명시한다.

10. **호재/악재 점수화**
    - 이벤트별 감성 라벨, 출처 신뢰도, 최신성, 반복 보도 여부를 기준으로 정성 점수를 계산한다.
    - 점수 계산은 Python 규칙으로 수행하고, LLM은 점수 자체를 만들지 않는다.
    - 결과는 `positive_drivers`, `negative_risks`, `neutral_watchpoints`로 나누어 저장한다.

11. **LLM 호출 계획**
    - 정상 비용 상태에서는 최대 3회 호출한다.
    - 1회차: 뉴스 이벤트 요약 및 호재/악재 분류.
    - 2회차: 공시 기반 사업 구조와 리스크 요약.
    - 3회차: 사용자용 최종 정성 리포트 문장화.
    - 40,000원 이상이면 뉴스+공시 통합 1회 호출로 축소한다.
    - 50,000원 이상이면 LLM 호출 없이 템플릿과 근거 목록만 제공한다.

12. **Guardrail 및 RAGAS 평가**
    - 출처 없는 투자 판단, 과장된 확정 표현, 직접적인 매수/매도 권유를 차단한다.
    - 백그라운드에서 RAGAS Faithfulness를 측정하고 목표 0.80 미만이면 결과에 검토 필요 플래그를 부여한다.
    - 사용자 화면에는 과도한 단정 대신 `가능성`, `리스크`, `확인 필요` 표현을 사용한다.

13. **QualReport 스키마 검증**
    - `QualReport` 스키마로 산업 요약, 이벤트 목록, 출처 목록, 리스크, 품질 플래그를 검증한다.
    - 출처 ID가 없는 핵심 주장이 있으면 저장을 차단하거나 해당 문장을 제거한다.

14. **결과 저장 및 반환**
    - `QualReport`를 `analysis_history`에 저장한다.
    - 최근 24시간 재사용을 위해 `analysis_cache`에 `feature_id`, `stock_code`, `analysis_window_days`, `retrieval_hash`, `expires_at`을 저장한다.
    - UI에는 산업 요약 카드, 뉴스 타임라인, 호재/악재 표, 공시 리스크, 출처 목록을 반환한다.

### 4.5 출력

| 출력 항목 | 타입 | 저장/렌더링 위치 | 설명 |
|-----------|------|------------------|------|
| `company_header` | object | UI | 종목명, 종목코드, 산업분류, 기준일 |
| `industry_summary` | string | UI/State/DB | 산업 구조와 사업 환경 요약 |
| `business_model_summary` | string | UI/State/DB | 주요 제품/서비스, 매출 동인, 고객 구조 요약 |
| `news_timeline` | table | UI/DB | 날짜순 뉴스 이벤트, 출처, 감성, 이벤트 유형 |
| `positive_drivers` | array | UI/State/DB | 호재 요인 목록과 근거 출처 |
| `negative_risks` | array | UI/State/DB | 악재/리스크 목록과 근거 출처 |
| `neutral_watchpoints` | array | UI/State/DB | 중립 감시 포인트 |
| `disclosure_risk_summary` | string/null | UI/State/DB | 공시 기반 리스크 요약 |
| `event_classification_table` | table | UI/DB | 9개 이벤트 유형별 분류 결과 |
| `source_citations` | array | UI/DB | 기사/공시 제목, 출처, URL, 발행일, 청크 ID |
| `rag_quality_flags` | array | UI/DB | 검색 부족, 출처 부족, 오래된 공시, 중복 기사 등 품질 플래그 |
| `faithfulness_score` | decimal/null | 운영/평가 | RAGAS Faithfulness 측정 결과 |
| `cache_status` | enum | UI/DB | `cache_hit`, `cache_miss`, `refreshed` |
| `QualReport` | object | LangGraph State/DB | A4, A6에서 재사용할 정성 분석 결과 |

### 4.6 예외 처리

| 예외 상황 | 감지 조건 | 처리 방안 | 사용자 표시 |
|-----------|-----------|-----------|-------------|
| 종목 없음 | `company` 조회 결과 0건 | 분석 중단, B3 검색으로 복귀 유도 | `지원하지 않는 종목입니다.` |
| 뉴스 데이터 없음 | 검색 기간 내 `rag_documents` 0건 | 공시 중심 분석으로 전환, 뉴스 섹션 비움 | `최근 뉴스 데이터가 부족합니다.` |
| 공시 데이터 없음 | `disclosure` 또는 공시 청크 0건 | 뉴스 중심 분석으로 계속 진행 | `공시 데이터가 없어 뉴스 기반으로만 분석했습니다.` |
| RAG 검색 결과 부족 | 유효 청크가 기준치 미만 | 검색 기간 확장 제안, 낮은 신뢰도 플래그 표시 | `근거 문서가 충분하지 않습니다.` |
| 중복 기사 과다 | 동일 제목/본문 비율 높음 | 중복 제거 후 대표 기사만 사용 | `동일 이슈 반복 보도는 하나로 묶었습니다.` |
| 오래된 공시 | 최신 공시 기준일이 1년 초과 | 공시 기준일 표시, 최신성 경고 | `공시 기준일이 오래되어 참고용입니다.` |
| 출처 URL 누락 | 문서 메타에 URL 없음 | 해당 청크는 핵심 주장 근거에서 제외 | `일부 출처는 링크를 제공하지 못했습니다.` |
| LLM 비용 3만원 도달 | 당월 사용액 >= 30,000원 | 검색 문서 수와 요약 길이 축소 | `비용 절감 모드로 요약이 간결하게 제공됩니다.` |
| LLM 비용 4만원 도달 | 당월 사용액 >= 40,000원 | LLM 호출 1회로 축소, 통합 요약 생성 | `비용 절감 정책에 따라 통합 요약으로 제공됩니다.` |
| LLM 비용 5만원 도달 | 당월 사용액 >= 50,000원 | LLM 호출 중지, 템플릿과 출처 목록만 제공 | `월 비용 상한 도달로 AI 요약 생성을 중지했습니다.` |
| LLM 실패/타임아웃 | 호출 실패 또는 제한 시간 초과 | 규칙 기반 이벤트 표와 원문 출처 제공 | `AI 요약에 실패해 근거 목록 중심으로 표시합니다.` |
| 환각 위험 감지 | 출처 없는 주장 또는 근거 불일치 | 해당 문장 제거, Guardrail 플래그 저장 | `일부 문장은 근거 부족으로 제외되었습니다.` |
| Faithfulness 미달 | RAGAS 점수 < 0.80 | 검토 필요 플래그, 운영 로그 저장 | `근거 일치도 검토가 필요한 결과입니다.` |
| Pydantic 검증 실패 | `QualReport` 필수 필드 누락 | 저장 중단, 원인 로깅, 재시도 버튼 제공 | `정성 분석 결과 검증에 실패했습니다.` |
| DB 저장 실패 | `analysis_history`/`analysis_cache` insert 실패 | UI 반환은 유지, 저장 실패 로깅 | `분석 결과 저장에 실패했습니다.` |

### 4.7 담당

| 영역 | 메인 담당 | 보조 담당 | 관련 테이블/모듈 | 설명 |
|------|-----------|-----------|------------------|------|
| 요청 라우팅 | Strategist | UI Controller | LangGraph State | B4/B5/A4에서 A2 실행 연결 |
| 뉴스 RAG | Qual Worker | Data Loader | `rag_documents`, `rag_chunks` | 뉴스 후보 검색, 중복 제거, 청크 선별 |
| 공시 RAG | Qual Worker | Data Loader | `disclosure`, `rag_chunks` | 사업보고서/분기보고서 근거 검색 |
| 이벤트 분류 | Qual Worker | Guardrail | LLM Gateway, 분류 규칙 | 9개 이벤트 유형 및 감성 라벨 분류 |
| 정성 점수화 | Qual Worker | Backend API | Python scoring module | 호재/악재/중립 포인트 산출 |
| 캐시 관리 | Qual Worker | Backend API | `analysis_cache`, `analysis_history` | 24시간 캐시 조회, 저장, 만료 관리 |
| 품질 평가 | Evaluator | Guardrail | RAGAS, `eval/golden_set` | Faithfulness 측정 및 검토 플래그 |
| 비용 제어 | Guardrail | Ops Monitor | `llm_cost_log` 또는 운영 집계 | 월 5만원 상한, 임계점별 호출 제한 |
| 리포트 연계 | Report Worker | Qual Worker | `QualReport` | A6 PB 리포트의 산업/뉴스 섹션 재사용 |
| 사용자 화면 | UI Controller | Qual Worker | Streamlit/Frontend | 카드, 타임라인, 출처, 품질 배지 렌더링 |

---

## 5. 기능-에이전트-DB-LLM 호출 매핑

| 단계 | 담당 에이전트 | DB/도구 | LLM 호출 | 비고 |
|------|---------------|---------|----------|------|
| 종목 검증 | Qual Worker | `company` | 0회 | 코드/회사명/산업 조회 |
| 캐시 조회 | Qual Worker | `analysis_cache`, `analysis_history` | 0회 | 24시간 내 동일 조건 결과 우선 |
| 뉴스 RAG 검색 | Qual Worker | `rag_documents`, `rag_chunks`, pgvector | 0회 | Hybrid Search |
| 공시 RAG 검색 | Qual Worker | `disclosure`, `rag_chunks`, pgvector | 0회 | 최신 공시 우선 |
| 뉴스 이벤트 요약 | Qual Worker | LLM Gateway | 최대 1회 | 비용 4만원 이상이면 통합 호출로 흡수 |
| 공시 리스크 요약 | Qual Worker | LLM Gateway | 최대 1회 | 공시 데이터 없으면 0회 |
| 최종 정성 리포트 | Qual Worker + Guardrail | LLM Gateway | 최대 1회 | 출처 기반 문장화 |
| RAGAS 평가 | Evaluator | RAGAS, `eval/golden_set` | 백그라운드 0~1회 | 운영 정책에 따라 비동기 |
| 이력 저장 | Qual Worker | `analysis_history`, `analysis_cache` | 0회 | A4/A6 재사용 |

---

## 6. KPI / 비용 상한 / 운영 기준

| 지표 | 목표 | 측정 방식 |
|------|------|-----------|
| 단일 종목 정성 분석 시간 | 60초 이내 | B4 클릭부터 A2 결과 렌더링 완료까지 |
| 캐시 적중 응답 시간 | 5초 이내 | 24시간 캐시 존재 시 UI 표시 완료까지 |
| LLM 호출 수 | A2 실행당 최대 3회 | LLM Gateway 호출 로그 |
| 월 LLM 비용 | 50,000원 이하 | 운영 비용 집계 |
| RAGAS Faithfulness | 0.80 이상 | 평가 하네스 자동 측정 |
| 출처 없는 핵심 주장 | 0건 | Guardrail 출처 검증 |
| 뉴스 중복 제거율 | 중복 후보 90% 이상 제거 | 문서 해시/제목 유사도 기준 |
| 공시 기준일 표시율 | 100% | 공시 섹션 렌더링 검증 |
| 스키마 검증 성공률 | 99% 이상 | `QualReport` 검증 로그 |

---

## 7. 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|-----------|
| 2026-05-23 | v0.8 | A2. 산업·정성 분석 기능별 상세 명세서 초안 작성 |

