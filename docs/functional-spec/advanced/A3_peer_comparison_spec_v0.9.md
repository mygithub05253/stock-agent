# 기능 명세서 v0.9 - A3. 동종업계 횡비교

| 항목 | 값 |
|------|-----|
| 작성자 | PM |
| 작성일 | 2026-05-23 |
| 버전 | v0.9 |
| 상위 문서 | `docs/prd/PRD_v0.6.md` |
| 참조 문서 | `docs/functional-spec/overview/functional_spec_all_features_v0.1.md`, `docs/functional-spec/advanced/A1_valuation_5y_spec_v0.7.md`, `docs/functional-spec/advanced/A2_industry_qualitative_spec_v0.8.md`, `docs/architecture/system_flow.md`, `docs/architecture/erd.md`, `docs/operations/llm_cost_guide.md` |
| 대상 사용자 | 개인투자자, PM, 개발팀, 데이터팀 |
| 기능 ID | `A3` |
| 기능명 | 동종업계 횡비교 |

---

## 0. 문서 메타 정보

본 문서는 PRD 기준 고급 기능 `A3. 동종업계 횡비교`의 상세 기능 명세서다. 기존 통합 초안의 7대 표준 양식인 **트리거 / 전제조건 / 입력 / 처리 흐름 / 출력 / 예외 처리 / 담당** 순서를 유지하고, Competitor Agent가 국내 동종업계 Peer를 추출해 대상 종목의 상대적 위치를 비교하는 흐름을 구체화한다.

`A3`는 사용자가 절대 수치만 보지 않고 같은 산업 내 경쟁사 대비 PER, PBR, ROE, 매출성장률, 영업이익률, 시가총액 위치를 비교하도록 돕는 기능이다. Peer 선정과 지표 계산은 Python/DB 기반 규칙으로 수행하며, LLM은 이미 계산된 비교 결과를 사용자 친화적인 위치 요약으로 바꾸는 데만 사용한다.

---

## 1. 문서 위치 / 작성 원칙

| 원칙 | 적용 방식 |
|------|-----------|
| Markdown 콘텐츠와 HTML 대시보드 분리 | 본 문서는 기능 명세 Markdown이며, Peer Heatmap 발표 대시보드는 별도 HTML로 관리한다. |
| 프롬프트와 코드 분리 | Peer 위치 요약 프롬프트는 코드에 직접 삽입하지 않고 문서 또는 프롬프트 폴더에 격리한다. |
| 기능별 파일 분리 | `A3` 단일 기능만 다루며 A1 적정가 계산, A2 뉴스·공시 분석, A4 권유 판단은 결과 연계만 명시한다. |
| 7대 표준 양식 준수 | 트리거, 전제조건, 입력, 처리 흐름, 출력, 예외 처리, 담당을 고정 순서로 작성한다. |
| 수치 계산 LLM 금지 | PER, PBR, ROE, 성장률, 분위수, 랭킹 계산은 Python으로 수행한다. |
| 비용 상한 명시 | A3 1회 실행당 LLM 호출은 최대 2회, 월 LLM 비용은 5만원 상한 내에서 제어한다. |
| MVP 범위 명확화 | MVP는 국내 Peer 3개 이상 비교를 목표로 하며 글로벌 Peer 비교는 제외한다. |

---

## 2. 기능 개요

동종업계 횡비교 기능은 특정 종목이 같은 산업 내 기업들과 비교했을 때 밸류에이션이 비싼지, 수익성이 좋은지, 성장성이 높은지, 규모가 큰지 한눈에 보여주는 기능이다. B4 종목 기본 정보, A1 밸류에이션, A4 통합 권유 플로우에서 호출될 수 있다.

MVP 화면은 대상 종목과 국내 Peer 기업 3개 이상의 비교 표, Peer Heatmap, 지표별 랭킹, 분위수, 사용자용 위치 요약으로 구성한다. Peer 데이터가 부족하면 가용 Peer만 비교하고, 비교 신뢰도를 낮게 표시한다.

---

## 3. 핵심 요약 표

| 항목 | 내용 |
|------|------|
| 기능명 | 동종업계 횡비교 |
| 기능 ID | `A3` |
| 목적 | 대상 종목의 밸류에이션·수익성·성장성·규모를 동종업계 Peer 대비 비교 |
| 주요 사용자 | 상대 비교를 통해 판단하려는 개인투자자, A4 종합 판단 사용자 |
| 주 트리거 | B4/A1 화면의 `동종업계 비교 보기`, A4 통합 분석 플로우의 Competitor Agent 호출 |
| 전제조건 | `company.sector`, Peer 종목 재무 데이터, 시세/시가총액 데이터 적재 |
| 주요 입력 | `stock_code`, `peer_selection_mode`, `metric_set`, 재무·시세 데이터 |
| 메인 에이전트 | Competitor Agent |
| 보조 에이전트 | Quant Worker, Strategist, Guardrail |
| 주요 DB | `company`, `financial_data`, `financial_statement`, `stock_price`, `analysis_cache`, `analysis_history` |
| 주요 출력 | Peer 비교표, Heatmap, 지표별 랭킹, 분위수, Peer 위치 요약, `CompetitorReport` |
| LLM 비용 정책 | 24시간 내 동일 종목 A3 결과 캐시 우선, 캐시 미스 시 최대 2회 |
| 월 비용 상한 | 전체 서비스 월 LLM 비용 50,000원 초과 방지 |
| MVP 범위 | 국내 같은 섹터 Peer 3개 이상 비교, 글로벌 Peer 제외 |
| 제외 범위 | 해외 Peer 비교, 최종 BUY/HOLD/SELL 판단, 산업 정성 RAG 요약 |

---

## 4. A3. 동종업계 횡비교

### 4.1 트리거

- 사용자가 B4 종목 기본 정보 화면에서 `동종업계 비교 보기`를 클릭한다.
- 사용자가 A1 5개년 밸류에이션 화면에서 상대가치평가 근거의 `Peer 상세 보기`를 클릭한다.
- 사용자가 A4 BUY/HOLD/SELL 권유 플로우에 진입했고, LangGraph가 경쟁사 비교 선행 작업으로 A3를 호출한다.
- 사용자가 B5 포트폴리오 일괄 안내 결과에서 특정 종목의 `경쟁사 대비 위치 보기`를 클릭한다.
- 사용자가 기존 Peer 비교 이력에서 `최신 데이터로 다시 비교`를 클릭한다.

### 4.2 전제조건

| 조건 | 상세 |
|------|------|
| 종목 코드 확정 | `stock_code`는 6자리 문자열이며 `company` 테이블에 존재해야 한다. |
| 섹터 정보 존재 | `company.sector` 또는 동등한 산업분류 값이 있어야 Peer 후보를 추출할 수 있다. |
| 국내 Peer 후보 존재 | 같은 섹터 내 대상 종목을 제외한 국내 상장사가 최소 1개 이상 있어야 한다. MVP 목표는 3개 이상이다. |
| 재무 데이터 적재 | 대상 종목과 Peer의 최근 3개년 이상 `financial_data` 또는 `financial_statement`가 있어야 한다. |
| 시세 데이터 적재 | 대상 종목과 Peer의 `stock_price`에 현재가, 시가총액, 기준일 데이터가 있어야 한다. |
| Quant 계산 모듈 준비 | PER, PBR, ROE, 매출성장률, 영업이익률, 부채비율, 분위수 계산 함수가 Python으로 구현되어 있어야 한다. |
| 비용 상태 확인 | 월 LLM 비용 집계가 5만원 상한을 초과하지 않아야 한다. 임계점 접근 시 LLM 위치 요약은 제한된다. |
| 캐시 조회 가능 | 동일 종목·동일 Peer 후보·동일 데이터 기준의 최근 24시간 A3 결과를 조회할 수 있어야 한다. |

### 4.3 입력

| 필드 | 타입 | 필수 | 출처 | 설명 |
|------|------|------|------|------|
| `stock_code` | string | Y | B4/A1/A4/B5 | 분석 대상 종목 코드. 6자리 숫자 문자열 |
| `user_id` | string/null | N | 세션 | 분석 이력 저장 및 개인화 연결용 사용자 ID |
| `peer_selection_mode` | enum | N | UI/기본값 | `same_sector`, `same_sector_marketcap_near`, `manual` |
| `manual_peer_codes` | array/null | N | UI | 사용자가 직접 지정한 Peer 종목 코드 목록 |
| `metric_set` | array | N | UI/기본값 | 비교 지표 목록. 기본 PER, PBR, ROE, 매출성장률, 영업이익률 |
| `min_peer_count` | integer | N | 시스템 기본값 | MVP 목표 최소 Peer 수. 기본 3개 |
| `max_peer_count` | integer | N | 시스템 기본값 | 비교 표 최대 Peer 수. 기본 8개 |
| `lookback_years` | integer | N | 시스템 기본값 | 재무 비교 기간. 기본 3년, 확장 시 5년 |
| `include_heatmap` | boolean | N | UI/기본값 | Peer Heatmap 렌더링 여부 |
| `force_refresh` | boolean | N | UI | 24시간 캐시를 무시하고 재계산할지 여부 |
| `company_profile` | object | Y | `company` | 종목명, 시장, 섹터, 업종 |
| `financial_rows` | array | Y | DB | 대상 종목과 Peer의 재무제표 주요 항목 |
| `price_rows` | array | Y | DB | 대상 종목과 Peer의 현재가, 시가총액, 기준일 |

### 4.4 처리 흐름

1. **요청 검증**
   - `stock_code` 형식이 6자리 숫자 문자열인지 확인한다.
   - `company`에서 대상 종목의 종목명, 시장구분, 섹터, 업종을 조회한다.
   - 대상 종목이 없거나 섹터가 없으면 Peer 비교를 시작하지 않고 예외 응답을 반환한다.

2. **월 LLM 비용 상태 확인**
   - 운영 비용 집계에서 당월 LLM 사용액을 조회한다.
   - 30,000원 이상이면 LLM 위치 요약 길이를 축소한다.
   - 40,000원 이상이면 LLM 호출을 1회로 제한하고 상세 해석 대신 핵심 위치 요약만 생성한다.
   - 50,000원 이상이면 LLM 호출을 중지하고 Python 계산표와 규칙 기반 문구만 제공한다.

3. **24시간 분석 캐시 우선 조회**
   - `analysis_cache` 또는 `analysis_history`에서 `feature_id = A3`, `stock_code`, `peer_set_hash`, `metric_set_hash`, `data_version`이 같은 최근 24시간 결과를 조회한다.
   - 캐시가 있고 `force_refresh = false`이면 Peer 추출, 지표 계산, LLM 호출을 생략한다.
   - 캐시된 `CompetitorReport`를 UI에 즉시 반환하고 `최근 Peer 비교 재사용` 배지를 표시한다.

4. **Peer 후보 추출**
   - 기본값은 `company.sector`가 같은 국내 상장사를 Peer 후보로 추출한다.
   - `same_sector_marketcap_near` 모드에서는 시가총액이 대상 종목의 0.25배~4배 범위에 있는 후보를 우선한다.
   - `manual` 모드에서는 사용자가 입력한 종목 코드가 `company`에 존재하고 대상 종목과 비교 가능한지 검증한다.
   - 글로벌 Peer는 MVP 범위에서 제외하고 v2 확장 대상으로 남긴다.

5. **Peer 후보 정렬 및 제한**
   - 후보가 `max_peer_count`를 초과하면 섹터 일치도, 시가총액 근접도, 재무 데이터 완성도 순으로 정렬한다.
   - 대상 종목과 사업 구조가 과도하게 다른 기업은 `low_similarity` 플래그를 부여한다.
   - 후보가 3개 미만이어도 분석은 진행하되 `Peer 부족` 경고를 표시한다.

6. **재무·시세 데이터 로딩**
   - 대상 종목과 Peer 후보의 최근 3개년 이상 매출, 영업이익, 순이익, 자본총계, 부채총계, EPS, BPS를 조회한다.
   - `stock_price`에서 최신 현재가, 시가총액, 기준일을 조회한다.
   - 데이터 기준일이 서로 다르면 가장 최신 공통 기준일 또는 각 지표의 기준일을 명시한다.

7. **비교 지표 계산**
   - Python으로 PER, PBR, ROE, 매출성장률, 영업이익률, 부채비율, 시가총액, 1년 주가수익률을 계산한다.
   - 결손 또는 음수 분모로 계산이 불가능한 지표는 `not_applicable`로 처리한다.
   - 계산식과 기준 기간은 `CompetitorReport.metric_definitions`에 저장한다.

8. **랭킹·분위수·Heatmap 생성**
   - 지표별로 대상 종목의 Peer 내 순위와 분위수를 계산한다.
   - PER/PBR은 낮을수록 저평가 가능성으로 표시하되, 적자 기업의 PER은 비교에서 제외한다.
   - ROE, 매출성장률, 영업이익률은 높을수록 우위로 표시한다.
   - Heatmap 색상은 지표별 방향성을 반영해 생성한다.

9. **A1 상대가치평가 연계**
   - A1이 실행 중이면 A3의 Peer PER/PBR 중앙값을 `QuantReport`의 상대가치평가 입력으로 제공한다.
   - A1이 이미 완료된 경우에는 A3 결과를 후속 참고 데이터로 저장하고 A1 결과를 자동 변경하지 않는다.

10. **LLM 위치 요약 생성**
    - 캐시가 없고 비용 임계점이 허용되는 경우에만 LLM을 최대 2회 호출한다.
    - 1회차는 Peer 선정 기준과 비교 지표의 의미를 요약한다.
    - 2회차는 대상 종목이 Peer 대비 저평가/고수익/고성장/고위험 중 어디에 가까운지 설명한다.
    - LLM은 계산값을 새로 만들지 않고 Python 계산표만 근거로 문장화한다.
    - 비용 임계점 초과, LLM 실패, 타임아웃 시 규칙 기반 템플릿 문구로 대체한다.

11. **Guardrail 검증**
    - 비교 우위가 곧 매수 권유처럼 읽히지 않도록 표현을 점검한다.
    - Peer가 3개 미만이거나 데이터 완성도가 낮으면 단정 표현을 금지한다.
    - “업계 최고”, “무조건 저평가” 같은 과장 표현을 차단한다.

12. **CompetitorReport 스키마 검증**
    - `CompetitorReport` 스키마로 Peer 목록, 지표표, 랭킹, 분위수, 데이터 품질 플래그를 검증한다.
    - 필수 지표가 모두 결손이면 저장을 중단하고 데이터 부족 예외를 반환한다.

13. **결과 저장 및 반환**
    - `CompetitorReport`를 `analysis_history`에 저장한다.
    - 최근 24시간 재사용을 위해 `analysis_cache`에 `feature_id`, `stock_code`, `peer_set_hash`, `metric_set_hash`, `data_version`, `expires_at`을 저장한다.
    - UI에는 Peer 비교표, Heatmap, 지표별 위치 요약, 데이터 품질 배지, A1/A4 연계 상태를 반환한다.

### 4.5 출력

| 출력 항목 | 타입 | 저장/렌더링 위치 | 설명 |
|-----------|------|------------------|------|
| `company_header` | object | UI | 대상 종목명, 종목코드, 섹터, 기준일 |
| `peer_selection_summary` | string | UI/State/DB | Peer 선정 기준과 제외 조건 요약 |
| `peer_list` | array | UI/State/DB | 비교 대상 Peer 종목 코드, 종목명, 섹터, 시가총액 |
| `comparison_table` | table | UI/DB | 대상 종목과 Peer의 PER, PBR, ROE, 성장률, 마진 비교 |
| `peer_heatmap` | object | UI | 지표별 상대 우위/열위 시각화 데이터 |
| `ranking_table` | table | UI/DB | 지표별 순위와 분위수 |
| `relative_position_summary` | string | UI/DB | Peer 대비 위치를 설명하는 사용자용 요약 |
| `metric_definitions` | object | UI/State/DB | 지표 계산식, 기준 기간, 방향성 |
| `data_quality_flags` | array | UI/DB | Peer 부족, 결손 지표, 오래된 데이터, 낮은 유사도 |
| `a1_peer_multiple_payload` | object/null | LangGraph State | A1 상대가치평가에 전달할 Peer PER/PBR 중앙값 |
| `cache_status` | enum | UI/DB | `cache_hit`, `cache_miss`, `refreshed` |
| `CompetitorReport` | object | LangGraph State/DB | A4, A6에서 재사용할 경쟁사 비교 결과 |

### 4.6 예외 처리

| 예외 상황 | 감지 조건 | 처리 방안 | 사용자 표시 |
|-----------|-----------|-----------|-------------|
| 종목 없음 | `company` 조회 결과 0건 | 분석 중단, B3 검색으로 복귀 유도 | `지원하지 않는 종목입니다.` |
| 섹터 정보 없음 | `company.sector` null | 자동 Peer 추출 중단, 수동 Peer 입력 제안 | `산업분류가 없어 자동 비교가 어렵습니다.` |
| Peer 후보 없음 | 같은 섹터 후보 0건 | 분석 중단 또는 수동 Peer 입력 유도 | `비교 가능한 동종업계 종목이 없습니다.` |
| Peer 3개 미만 | 유효 Peer 1~2개 | 가용 Peer만 비교, 신뢰도 낮음 표시 | `Peer 수가 부족해 참고용으로만 표시합니다.` |
| 재무 데이터 부족 | 대상 또는 Peer의 재무 데이터 3년 미만 | 해당 Peer 제외, 대상 종목 데이터 부족 시 분석 중단 | `일부 기업은 재무 데이터 부족으로 제외되었습니다.` |
| 시세 데이터 부족 | 현재가/시가총액 결손 | PER/PBR/시총 비교 제외, 나머지 지표만 표시 | `시세 데이터가 부족한 지표는 제외했습니다.` |
| 적자 기업 PER 왜곡 | 순이익 <= 0 | PER `not_applicable`, PBR/매출성장 중심 비교 | `적자 기업의 PER은 비교에서 제외했습니다.` |
| 극단치 존재 | 지표가 Peer 중앙값의 10배 초과 | Winsorize 또는 이상치 플래그 표시 | `일부 지표는 이상치 가능성이 있어 별도 표시했습니다.` |
| Peer 유사도 낮음 | 섹터는 같지만 사업 구조 차이 큼 | `low_similarity` 플래그 표시, 요약 문구 보수화 | `일부 Peer는 사업 구조가 달라 비교 신뢰도가 낮습니다.` |
| LLM 비용 3만원 도달 | 당월 사용액 >= 30,000원 | 위치 요약 길이 축소 | `비용 절감 모드로 요약이 간결하게 제공됩니다.` |
| LLM 비용 4만원 도달 | 당월 사용액 >= 40,000원 | LLM 호출 1회로 축소 | `비용 절감 정책에 따라 핵심 요약만 제공됩니다.` |
| LLM 비용 5만원 도달 | 당월 사용액 >= 50,000원 | LLM 호출 중지, 계산표와 템플릿 문구 제공 | `월 비용 상한 도달로 AI 요약 생성을 중지했습니다.` |
| LLM 실패/타임아웃 | 호출 실패 또는 제한 시간 초과 | 규칙 기반 위치 요약으로 대체 | `AI 요약에 실패해 기본 비교 설명을 표시합니다.` |
| Pydantic 검증 실패 | `CompetitorReport` 필수 필드 누락 | 저장 중단, 원인 로깅, 재시도 버튼 제공 | `경쟁사 비교 결과 검증에 실패했습니다.` |
| DB 저장 실패 | `analysis_history`/`analysis_cache` insert 실패 | UI 반환은 유지, 저장 실패 로깅 | `분석 결과 저장에 실패했습니다.` |

### 4.7 담당

| 영역 | 메인 담당 | 보조 담당 | 관련 테이블/모듈 | 설명 |
|------|-----------|-----------|------------------|------|
| 요청 라우팅 | Strategist | UI Controller | LangGraph State | B4/A1/A4/B5에서 A3 실행 연결 |
| Peer 추출 | Competitor Agent | Data Loader | `company`, `stock_price` | 섹터, 시가총액, 데이터 완성도 기반 후보 선정 |
| 지표 계산 | Competitor Agent | Quant Worker | `financial_data`, `financial_statement`, `stock_price` | PER, PBR, ROE, 성장률, 마진 계산 |
| Heatmap 생성 | Competitor Agent | UI Controller | Python visualization data | 지표 방향성 기반 색상/랭킹 데이터 생성 |
| A1 연계 | Competitor Agent | Quant Worker | `QuantReport`, `CompetitorReport` | Peer Multiple을 A1 상대가치평가에 제공 |
| 캐시 관리 | Competitor Agent | Backend API | `analysis_cache`, `analysis_history` | 24시간 캐시 조회, 저장, 만료 관리 |
| 요약 생성 | Competitor Agent | Guardrail | LLM Gateway, Prompt Store | 비교 결과를 사용자용 문장으로 변환 |
| 비용 제어 | Guardrail | Ops Monitor | `llm_cost_log` 또는 운영 집계 | 월 5만원 상한, 임계점별 호출 제한 |
| 리포트 연계 | Report Worker | Competitor Agent | `CompetitorReport` | A6 PB 리포트의 Peer 섹션 재사용 |
| 사용자 화면 | UI Controller | Competitor Agent | Streamlit/Frontend | 표, Heatmap, 랭킹, 품질 배지 렌더링 |

---

## 5. 기능-에이전트-DB-LLM 호출 매핑

| 단계 | 담당 에이전트 | DB/도구 | LLM 호출 | 비고 |
|------|---------------|---------|----------|------|
| 종목 검증 | Competitor Agent | `company` | 0회 | 코드/회사명/섹터 조회 |
| 캐시 조회 | Competitor Agent | `analysis_cache`, `analysis_history` | 0회 | 24시간 내 동일 조건 결과 우선 |
| Peer 후보 추출 | Competitor Agent | `company`, `stock_price` | 0회 | 국내 같은 섹터 중심 |
| 재무·시세 로딩 | Competitor Agent | `financial_data`, `financial_statement`, `stock_price` | 0회 | 대상+Peer 데이터 |
| 비교 지표 계산 | Competitor Agent | Python 계산 모듈 | 0회 | 수치 계산은 LLM 금지 |
| Peer 위치 요약 | Competitor Agent + Guardrail | LLM Gateway | 최대 2회 | 비용 임계점 초과 시 템플릿 대체 |
| A1 연계 | Competitor Agent | LangGraph State | 0회 | Peer Multiple 전달 |
| 이력 저장 | Competitor Agent | `analysis_history`, `analysis_cache` | 0회 | A4/A6 재사용 |

---

## 6. KPI / 비용 상한 / 운영 기준

| 지표 | 목표 | 측정 방식 |
|------|------|-----------|
| 단일 종목 Peer 비교 시간 | 30초 이내 | 트리거부터 A3 결과 렌더링 완료까지 |
| 캐시 적중 응답 시간 | 5초 이내 | 24시간 캐시 존재 시 UI 표시 완료까지 |
| LLM 호출 수 | A3 실행당 최대 2회 | LLM Gateway 호출 로그 |
| 월 LLM 비용 | 50,000원 이하 | 운영 비용 집계 |
| 국내 Peer 확보율 | 대상 종목의 80% 이상에서 3개 이상 | Peer 추출 로그 |
| 지표 계산 성공률 | 핵심 지표 5개 중 4개 이상 계산 | `CompetitorReport` 검증 |
| Peer 부족 배지 표시율 | Peer 3개 미만 케이스 100% | UI 렌더링 검증 |
| 수치 계산 재현성 | 동일 입력 동일 결과 100% | `peer_set_hash`, `metric_set_hash`, `data_version` 기준 비교 |
| 스키마 검증 성공률 | 99% 이상 | `CompetitorReport` 검증 로그 |

---

## 7. 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|-----------|
| 2026-05-23 | v0.9 | A3. 동종업계 횡비교 기능별 상세 명세서 초안 작성 |

