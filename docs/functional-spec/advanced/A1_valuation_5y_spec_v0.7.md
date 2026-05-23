# 기능 명세서 v0.7 - A1. 5개년 밸류에이션

| 항목 | 값 |
|------|-----|
| 작성자 | PM |
| 작성일 | 2026-05-23 |
| 버전 | v0.7 |
| 상위 문서 | `docs/prd/PRD_v0.6.md` |
| 참조 문서 | `docs/functional-spec/overview/functional_spec_all_features_v0.1.md`, `docs/functional-spec/basic/B4_stock_basic_info_spec_v0.6.md`, `docs/architecture/system_flow.md`, `docs/architecture/erd.md`, `docs/operations/llm_cost_guide.md` |
| 대상 사용자 | 개인투자자, PM, 개발팀, 데이터팀 |
| 기능 ID | `A1` |
| 기능명 | 5개년 밸류에이션 |

---

## 0. 문서 메타 정보

본 문서는 PRD 기준 고급 기능 `A1. 5개년 밸류에이션`의 상세 기능 명세서다. 기존 통합 초안의 7대 표준 양식인 **트리거 / 전제조건 / 입력 / 처리 흐름 / 출력 / 예외 처리 / 담당** 순서를 유지하고, B4 종목 기본 정보 조회 이후 사용자가 정량 분석으로 진입하는 흐름을 구체화한다.

`A1`은 주가와 재무제표 기반의 정량 가치평가 기능이다. 계산은 Python 기반 Quant Worker가 수행하고, LLM은 계산 결과를 사용자가 이해할 수 있는 문장으로 설명하는 용도에만 제한한다. 월 LLM 비용 5만원 상한 정책을 지키기 위해 분석 캐시, 비용 임계점, 템플릿 대체 응답을 명시한다.

---

## 1. 문서 위치 / 작성 원칙

| 원칙 | 적용 방식 |
|------|-----------|
| Markdown 콘텐츠와 HTML 대시보드 분리 | 본 문서는 기능 명세 Markdown이며, 발표/현황 대시보드는 별도 HTML로 관리한다. |
| 프롬프트와 코드 분리 | LLM 설명 프롬프트는 코드에 직접 삽입하지 않고 향후 `docs/prompts/` 또는 운영 문서 하위에 별도 관리한다. |
| 기능별 파일 분리 | `A1` 단일 기능만 다루며 A2, A3, A4의 판단 로직은 본문에 섞지 않는다. |
| 7대 표준 양식 준수 | 트리거, 전제조건, 입력, 처리 흐름, 출력, 예외 처리, 담당을 고정 순서로 작성한다. |
| 비용 상한 명시 | A1 1회 실행당 LLM 호출은 최대 1회, 월 LLM 비용은 5만원 상한 내에서 제어한다. |
| MVP 범위 명확화 | MVP는 3개년 이상 데이터로 계산 가능하게 하되, 화면에는 데이터 기간 제한을 명시한다. 최종 목표는 5개년 밸류에이션이다. |

---

## 2. 기능 개요

5개년 밸류에이션 기능은 사용자가 특정 종목에 대해 현재 주가가 내재가치 대비 고평가인지, 저평가인지, 또는 적정 수준인지 정량적으로 판단할 수 있도록 돕는 기능이다.

MVP에서는 B4 종목 기본 정보 화면의 `이 종목 분석하기` 버튼을 통해 진입하며, Quant Worker가 재무제표, 시가총액, 현재가, 주식 수, 배당 정보, Peer Multiple을 조회해 DCF, 상대가치평가, 배당할인모형 적용 가능성을 계산한다. LLM은 최종 계산값과 주요 가정을 짧은 설명 문단으로 바꾸는 데만 사용한다.

---

## 3. 핵심 요약 표

| 항목 | 내용 |
|------|------|
| 기능명 | 5개년 밸류에이션 |
| 기능 ID | `A1` |
| 목적 | 종목의 내재가치, 시나리오별 적정가, 안전마진을 정량적으로 산출 |
| 주요 사용자 | B4에서 종목 상세를 확인한 개인투자자, PB 리포트를 생성하려는 사용자 |
| 주 트리거 | B4 종목 기본 정보 화면의 `이 종목 분석하기` 클릭 |
| 전제조건 | `company` 종목 마스터, 3~5개년 재무제표, 현재가/시가총액, Quant Worker 계산 모듈 준비 |
| 주요 입력 | `stock_code`, `user_id`, 재무제표, 주가, 시가총액, 밸류에이션 가정값 |
| 메인 에이전트 | Quant Worker |
| 보조 에이전트 | Strategist, Guardrail, Report Worker |
| 주요 DB | `company`, `financial_data`, `financial_statement`, `stock_price`, `analysis_cache`, `analysis_history` |
| 주요 출력 | 시나리오별 적정가, 가중 평균 적정가, 안전마진, 방법론별 산출값, Excel 8시트 |
| LLM 비용 정책 | 24시간 내 동일 종목 A1 결과 캐시 우선, 캐시 미스 시 설명 생성 최대 1회 |
| 월 비용 상한 | 전체 서비스 월 LLM 비용 50,000원 초과 방지 |
| MVP 범위 | 3개년 이상 데이터 기반 산출, DCF/상대가치평가 우선, DDM은 조건 충족 시만 적용 |
| 제외 범위 | 최종 BUY/HOLD/SELL 판단, 산업 정성 분석, 동종업계 심층 횡비교, 종목 추천 |

---

## 4. A1. 5개년 밸류에이션

### 4.1 트리거

- 사용자가 B4 종목 기본 정보 화면에서 `이 종목 분석하기` 버튼을 클릭한다.
- 사용자가 B5 포트폴리오 일괄 안내 결과에서 특정 종목의 `밸류에이션 보기`를 클릭한다.
- 사용자가 A4 BUY/HOLD/SELL 권유 플로우에 진입했고, LangGraph가 선행 정량 분석으로 A1을 호출한다.
- 사용자가 기존 분석 이력에서 `최신 데이터로 다시 계산`을 클릭한다.

### 4.2 전제조건

| 조건 | 상세 |
|------|------|
| 종목 코드 확정 | `stock_code`는 6자리 문자열이며 `company` 테이블에 존재해야 한다. |
| 재무 데이터 적재 | `financial_data` 또는 `financial_statement`에 최근 3개년 이상 연간 재무제표가 있어야 한다. |
| 5개년 목표 데이터 | 5개년 데이터가 있으면 전체 5개년 밸류에이션을 수행하고, 3~4개년만 있으면 제한 분석으로 표시한다. |
| 시세 데이터 적재 | `stock_price`에 현재가, 기준일, 시가총액 또는 산출 가능한 주식 수 정보가 있어야 한다. |
| Quant Worker 준비 | DCF, 상대가치평가, DDM, 시나리오 계산 함수가 Python으로 구현되어 있어야 한다. |
| 비용 상태 확인 | 월 LLM 비용 집계가 5만원 상한을 초과하지 않아야 한다. 임계점 접근 시 LLM 설명 생성은 제한된다. |
| 캐시 조회 가능 | 동일 종목·동일 데이터 기준의 최근 24시간 A1 분석 결과를 조회할 수 있어야 한다. |
| 사용자 세션 | 비회원 조회를 허용하지 않는 운영 정책이면 `user_id`가 유효해야 한다. |

### 4.3 입력

| 필드 | 타입 | 필수 | 출처 | 설명 |
|------|------|------|------|------|
| `stock_code` | string | Y | B4/B5/A4 | 분석 대상 종목 코드. 6자리 숫자 문자열 |
| `user_id` | string/null | N | 세션 | 분석 이력 저장 및 개인화 연결용 사용자 ID |
| `valuation_period_years` | integer | N | UI/기본값 | 목표 분석 기간. 기본 5년, MVP 최소 3년 |
| `scenario_set` | enum | N | 시스템 기본값 | `conservative`, `base`, `aggressive` 3개 시나리오 |
| `discount_rate_override` | decimal/null | N | 고급 설정 | WACC 수동 입력값. 미입력 시 산업/시장 기본 가정 사용 |
| `terminal_growth_override` | decimal/null | N | 고급 설정 | 영구성장률 수동 입력값. 미입력 시 보수적 기본값 사용 |
| `use_peer_multiple` | boolean | N | UI/기본값 | PER/PBR 상대가치평가 사용 여부. 기본 `true` |
| `use_ddm` | boolean | N | UI/기본값 | 배당할인모형 사용 여부. 안정 배당주에 한해 실제 적용 |
| `export_excel` | boolean | N | UI | Excel 8시트 다운로드 생성 여부 |
| `force_refresh` | boolean | N | UI | 24시간 캐시를 무시하고 재계산할지 여부 |
| `financial_rows` | array | Y | DB | 손익계산서, 재무상태표, 현금흐름표 주요 항목 |
| `price_snapshot` | object | Y | DB | 현재가, 기준일, 시가총액, 거래량, 주식 수 |
| `peer_multiple_rows` | array/null | N | DB/A3 연계 | Peer PER/PBR/EV/EBITDA. 없으면 상대가치평가 가중치 축소 |

### 4.4 처리 흐름

1. **요청 검증**
   - `stock_code` 형식이 6자리 숫자 문자열인지 확인한다.
   - `company` 테이블에서 종목명, 시장구분, 산업분류, DART 고유번호를 조회한다.
   - 종목이 없으면 A1 계산을 시작하지 않고 예외 응답을 반환한다.

2. **월 LLM 비용 상태 확인**
   - 운영 비용 집계에서 당월 LLM 사용액을 조회한다.
   - 30,000원 이상이면 캐시 재사용을 우선하고 LLM 설명 문단 길이를 축소한다.
   - 40,000원 이상이면 신규 LLM 호출을 기본 차단하고 템플릿 설명을 사용한다.
   - 50,000원 이상이면 A1의 LLM 호출을 전면 중지하며 Python 계산 결과만 제공한다.

3. **24시간 분석 캐시 우선 조회**
   - `analysis_cache` 또는 `analysis_history`에서 `feature_id = A1`, `stock_code`, `data_version`, `assumption_hash`가 같은 최근 24시간 결과를 조회한다.
   - 캐시가 있고 `force_refresh = false`이면 Quant Worker 재계산과 LLM 호출을 생략한다.
   - 캐시된 `QuantReport`를 UI에 즉시 반환하고, 필요 시 Excel 파일만 재생성한다.
   - 캐시 사용 여부와 기준 시각을 화면에 `최근 분석 재사용` 배지로 표시한다.

4. **재무제표 데이터 로딩**
   - `financial_data` 또는 `financial_statement`에서 최근 연간 손익계산서, 재무상태표, 현금흐름표를 조회한다.
   - 매출, 영업이익, 순이익, 자본총계, 부채총계, 영업현금흐름, 투자현금흐름, CAPEX, 배당금 항목을 표준 스키마로 정규화한다.
   - 5개년 데이터가 있으면 `period_coverage = 5Y`, 3~4개년만 있으면 `period_coverage = LIMITED`로 표시한다.

5. **시세 및 시가총액 데이터 로딩**
   - `stock_price`에서 최신 종가, 기준일, 시가총액, 거래대금을 조회한다.
   - 주식 수가 별도 저장되어 있지 않으면 `market_cap / close_price`로 추정하되, 추정값임을 결과 메타에 남긴다.

6. **기초 재무지표 계산**
   - Python으로 매출 CAGR, 영업이익률, 순이익률, EPS, BPS, ROE, 부채비율, FCF, FCF Margin을 계산한다.
   - 계산값이 결손 또는 비정상 범위이면 해당 항목에 `insufficient_data` 플래그를 부여한다.
   - 이 단계에서는 LLM을 호출하지 않는다.

7. **시나리오 가정 생성**
   - 보수, 기준, 공격 시나리오별 매출 성장률, 영업이익률, 세율, 재투자율, WACC, 영구성장률을 생성한다.
   - 기본 가정은 과거 3~5개년 지표의 중앙값과 보수적 상·하한으로 산출한다.
   - 사용자가 WACC 또는 영구성장률을 수동 입력한 경우 허용 범위 검증 후 반영한다.

8. **DCF 계산**
   - 시나리오별 향후 5년 FCF를 추정한다.
   - WACC로 미래 FCF와 Terminal Value를 현재가치로 할인한다.
   - 순현금 또는 순차입금을 반영해 지분가치를 계산하고, 주식 수로 나누어 주당 적정가를 산출한다.
   - FCF가 지속적으로 음수이면 DCF 결과는 `not_applicable`로 처리한다.

9. **상대가치평가 계산**
   - Peer PER/PBR이 있으면 Peer 중앙값과 대상 종목 EPS/BPS를 곱해 적정가를 산출한다.
   - Peer 데이터가 없으면 동일 산업 기본 Multiple 또는 시장 평균을 사용하지 않고 상대가치평가 가중치를 축소한다.
   - A3 동종업계 횡비교가 구현된 이후에는 A3의 `CompetitorReport`를 우선 사용한다.

10. **DDM 적용 가능성 판정**
    - 최근 3년 이상 배당금이 존재하고 배당성향이 과도하게 흔들리지 않는 경우에만 DDM을 적용한다.
    - 무배당 또는 불안정 배당 종목은 DDM을 제외하고 사유를 출력한다.

11. **가중 평균 적정가 및 안전마진 계산**
    - 적용 가능한 방법론별 적정가에 가중치를 부여한다.
    - 기본 가중치는 DCF 60%, 상대가치평가 30%, DDM 10%이며, 적용 불가 방법론이 있으면 남은 방법론으로 재정규화한다.
    - 안전마진은 `(가중 평균 적정가 - 현재가) / 현재가`로 계산한다.

12. **LLM 설명 생성**
    - 캐시가 없고 비용 임계점이 허용되는 경우에만 LLM을 최대 1회 호출한다.
    - 입력에는 계산된 수치, 시나리오 가정, 제외된 방법론 사유만 전달한다.
    - LLM은 새로운 수치를 생성하지 않고, Python 계산 결과를 쉬운 한국어 설명으로 변환한다.
    - 비용 임계점 초과, LLM 실패, 타임아웃 시 사전 정의 템플릿 설명으로 대체한다.

13. **Pydantic 스키마 검증**
    - `QuantReport` 스키마로 계산 결과를 검증한다.
    - 필수 필드 누락, 음수 주식 수, 비정상 WACC, JSON 직렬화 오류가 있으면 저장 전 실패 처리한다.

14. **Excel 8시트 생성**
    - `export_excel = true`이면 `openpyxl` 기반으로 8개 시트를 생성한다.
    - 시트 구성은 `Assumptions`, `IncomeStatement`, `BalanceSheet`, `CashFlow`, `DCF`, `RelativeValuation`, `Scenarios`, `Sensitivity`로 한다.
    - Excel 생성 실패는 UI 결과 노출을 막지 않고 다운로드 버튼만 비활성화한다.

15. **결과 저장 및 반환**
    - `QuantReport`를 `analysis_history`에 저장한다.
    - 최근 24시간 재사용을 위해 `analysis_cache`에 `feature_id`, `stock_code`, `data_version`, `assumption_hash`, `expires_at`을 저장한다.
    - UI에는 핵심 카드, 시나리오 표, 방법론별 결과, 설명 문단, 다운로드 버튼을 반환한다.

### 4.5 출력

| 출력 항목 | 타입 | 저장/렌더링 위치 | 설명 |
|-----------|------|------------------|------|
| `company_header` | object | UI | 종목명, 종목코드, 시장구분, 기준일 |
| `period_coverage_badge` | enum | UI | `5개년`, `4개년 제한`, `3개년 제한` 등 데이터 범위 표시 |
| `current_price` | integer/decimal | UI/State | 기준일 현재가 또는 종가 |
| `weighted_fair_value` | integer/decimal | UI/State/DB | 방법론별 가중 평균 주당 적정가 |
| `margin_of_safety` | decimal | UI/State/DB | 현재가 대비 안전마진 |
| `scenario_table` | table | UI/Excel | 보수, 기준, 공격 시나리오별 적정가와 주요 가정 |
| `method_result_table` | table | UI/Excel | DCF, 상대가치평가, DDM 적용 여부와 산출값 |
| `sensitivity_table` | table | UI/Excel | WACC와 영구성장률 변화에 따른 DCF 민감도 |
| `valuation_summary_text` | string | UI/DB | LLM 또는 템플릿으로 생성된 한 문단 설명 |
| `excluded_methods` | array | UI/State | 적용 제외된 방법론과 사유 |
| `data_quality_flags` | array | UI/State/DB | 결손, 추정값, 제한 분석 여부 |
| `excel_file_path` | string/null | UI/DB | Excel 8시트 다운로드 파일 경로 |
| `cache_status` | enum | UI/DB | `cache_hit`, `cache_miss`, `refreshed` |
| `QuantReport` | object | LangGraph State/DB | A4, A6에서 재사용할 정량 분석 결과 |

### 4.6 예외 처리

| 예외 상황 | 감지 조건 | 처리 방안 | 사용자 표시 |
|-----------|-----------|-----------|-------------|
| 종목 없음 | `company` 조회 결과 0건 | 계산 중단, B3 검색으로 복귀 유도 | `지원하지 않는 종목입니다.` |
| 재무 데이터 3년 미만 | 연간 재무제표가 0~2개년 | A1 계산 중단, 데이터 부족 상태 저장 | `밸류에이션에 필요한 재무 데이터가 부족합니다.` |
| 재무 데이터 3~4년만 존재 | 5개년 미만이지만 3개년 이상 | 제한 분석 수행, 기간 배지 표시 | `현재는 3개년/4개년 데이터 기준 분석입니다.` |
| 현재가 없음 | 최신 `stock_price.close_price` 없음 | 적정가 계산은 가능 시 수행, 안전마진은 제외 | `현재가가 없어 안전마진을 계산하지 못했습니다.` |
| 시가총액 없음 | `market_cap` 결손 및 주식 수 추정 불가 | 주당 적정가 산출 제한, 방법론 일부 제외 | `시가총액 데이터가 부족합니다.` |
| FCF 지속 음수 | 최근 3년 누적 FCF 또는 영업이익이 음수 | DCF 제외, 상대가치평가 중심으로 재가중 | `DCF 적용이 제한되었습니다.` |
| Peer 데이터 없음 | Peer Multiple 0건 | 상대가치평가 제외 또는 가중치 0 처리 | `비교 기업 데이터가 없어 상대가치평가를 제외했습니다.` |
| 배당 데이터 없음 | 배당금 0 또는 결손 | DDM 제외 | `배당할인모형은 적용하지 않았습니다.` |
| WACC/영구성장률 비정상 | WACC <= g 또는 허용 범위 초과 | 기본값으로 대체하거나 사용자 입력 거절 | `가정값 범위를 확인해 주세요.` |
| 계산 결과 이상치 | 적정가가 현재가의 0.1배 미만 또는 10배 초과 | 결과에 이상치 플래그 부여, 설명 문구 보수화 | `일부 계산값은 변동성이 커 참고용으로만 표시됩니다.` |
| LLM 비용 3만원 도달 | 당월 사용액 >= 30,000원 | 캐시 우선, 설명 길이 축소 | `비용 절감 모드로 설명이 간결하게 제공됩니다.` |
| LLM 비용 4만원 도달 | 당월 사용액 >= 40,000원 | 신규 LLM 호출 차단, 템플릿 설명 사용 | `비용 절감 정책에 따라 자동 설명을 사용했습니다.` |
| LLM 비용 5만원 도달 | 당월 사용액 >= 50,000원 | LLM 호출 전면 중지, 계산 결과만 제공 | `월 비용 상한 도달로 AI 설명 생성을 중지했습니다.` |
| LLM 실패/타임아웃 | 호출 실패 또는 제한 시간 초과 | 템플릿 설명 대체, 계산 결과 유지 | `설명 생성에 실패해 기본 설명을 표시합니다.` |
| Pydantic 검증 실패 | `QuantReport` 필수 필드 누락 | 저장 중단, 원인 로깅, 재시도 버튼 제공 | `분석 결과 검증에 실패했습니다.` |
| Excel 생성 실패 | 파일 저장 또는 시트 생성 오류 | UI 결과는 표시, 다운로드만 비활성화 | `엑셀 파일 생성에 실패했습니다.` |
| DB 저장 실패 | `analysis_history`/`analysis_cache` insert 실패 | UI 반환은 유지, 저장 실패 로깅 | `분석 결과 저장에 실패했습니다.` |

### 4.7 담당

| 영역 | 메인 담당 | 보조 담당 | 관련 테이블/모듈 | 설명 |
|------|-----------|-----------|------------------|------|
| 요청 라우팅 | Strategist | UI Controller | LangGraph State | B4/B5/A4에서 A1 실행을 연결 |
| 정량 계산 | Quant Worker | - | `financial_data`, `financial_statement`, `stock_price` | DCF, Multiple, DDM, 안전마진 계산 |
| 데이터 조회 | Quant Worker | Data Loader | `company`, `financial_data`, `stock_price` | 종목/재무/시세 데이터 조회 및 정규화 |
| 캐시 관리 | Quant Worker | Backend API | `analysis_cache`, `analysis_history` | 24시간 캐시 조회, 저장, 만료 관리 |
| 설명 생성 | Quant Worker | Guardrail | LLM Gateway, Prompt Store | 계산 결과를 한 문단 설명으로 변환 |
| 비용 제어 | Guardrail | Ops Monitor | `llm_cost_log` 또는 운영 집계 | 월 5만원 상한, 임계점별 호출 제한 |
| 리포트 연계 | Report Worker | Quant Worker | Excel Writer, `QuantReport` | Excel 8시트 및 A6 PB 리포트 재사용 |
| 사용자 화면 | UI Controller | Quant Worker | Streamlit/Frontend | 카드, 표, 배지, 다운로드 버튼 렌더링 |

---

## 5. 기능-에이전트-DB-LLM 호출 매핑

| 단계 | 담당 에이전트 | DB/도구 | LLM 호출 | 비고 |
|------|---------------|---------|----------|------|
| 종목 검증 | Quant Worker | `company` | 0회 | 코드/회사명 검증 |
| 캐시 조회 | Quant Worker | `analysis_cache`, `analysis_history` | 0회 | 24시간 내 동일 조건 결과 우선 |
| 재무 데이터 로딩 | Quant Worker | `financial_data`, `financial_statement` | 0회 | 3~5개년 재무제표 |
| 시세 데이터 로딩 | Quant Worker | `stock_price` | 0회 | 현재가, 시가총액 |
| DCF/Multiple/DDM 계산 | Quant Worker | Python 계산 모듈 | 0회 | 수치 계산은 LLM 금지 |
| 결과 설명 | Quant Worker + Guardrail | LLM Gateway | 최대 1회 | 비용 임계점 초과 시 템플릿 대체 |
| Excel 생성 | Report Worker | `openpyxl` | 0회 | 8시트 생성 |
| 이력 저장 | Quant Worker | `analysis_history`, `analysis_cache` | 0회 | A4/A6 재사용 |

---

## 6. KPI / 비용 상한 / 운영 기준

| 지표 | 목표 | 측정 방식 |
|------|------|-----------|
| 단일 종목 분석 시간 | 60초 이내 | B4 클릭부터 A1 결과 렌더링 완료까지 |
| 캐시 적중 응답 시간 | 5초 이내 | 24시간 캐시 존재 시 UI 표시 완료까지 |
| LLM 호출 수 | A1 실행당 최대 1회 | LLM Gateway 호출 로그 |
| 월 LLM 비용 | 50,000원 이하 | 운영 비용 집계 |
| 계산 재현성 | 동일 입력 동일 결과 100% | `assumption_hash`, `data_version` 기준 비교 |
| 데이터 범위 표시 | 제한 분석 표시 100% | 5개년 미만 데이터에서 배지 노출 여부 |
| Excel 생성 성공률 | 95% 이상 | 다운로드 파일 생성 로그 |
| 스키마 검증 성공률 | 99% 이상 | `QuantReport` 검증 로그 |

---

## 7. 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|-----------|
| 2026-05-23 | v0.7 | A1. 5개년 밸류에이션 기능별 상세 명세서 초안 작성 |

