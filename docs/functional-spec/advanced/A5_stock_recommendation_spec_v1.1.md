# 기능 명세서 v1.1 - A5. 종목 추천

| 항목 | 값 |
|------|-----|
| 작성자 | PM |
| 작성일 | 2026-05-23 |
| 버전 | v1.1 |
| 상위 문서 | `docs/prd/PRD_v0.6.md` |
| 참조 문서 | `docs/functional-spec/overview/functional_spec_all_features_v0.1.md`, `docs/functional-spec/basic/B1_signup_login_spec_v0.3.md`, `docs/functional-spec/basic/B2_holdings_manage_spec_v0.4.md`, `docs/functional-spec/basic/B3_stock_search_spec_v0.5.md`, `docs/functional-spec/advanced/A4_action_recommendation_spec_v1.0.md`, `docs/architecture/system_flow.md`, `docs/architecture/erd.md`, `docs/operations/llm_cost_guide.md` |
| 대상 사용자 | 종목을 아직 정하지 못한 개인투자자, PM, 개발팀 |
| 기능 ID | `A5` |
| 기능명 | 종목 추천 |

---

## 0. 문서 메타 정보

본 문서는 PRD 기준 고급 기능 `A5. 종목 추천`의 상세 기능 명세서다. 기존 통합 초안의 7대 표준 양식인 **트리거 / 전제조건 / 입력 / 처리 흐름 / 출력 / 예외 처리 / 담당** 순서를 유지하고, Curator Agent가 사용자의 자연어 의도와 투자성향, 관심 섹터, 시장 데이터를 바탕으로 5~10개 후보 종목을 제안하는 흐름을 구체화한다.

`A5`는 사용자가 아직 특정 종목을 고르지 못했을 때 분석 시작점을 제공하는 기능이다. 여러 종목을 동시에 평가할 수 있어 비용 폭발과 API 타임아웃 위험이 있으므로, 1차 후보 스크리닝은 DB/Python 규칙으로 수행하고 LLM은 의도 파싱과 최종 추천 사유 문장화에만 제한한다.

---

## 1. 문서 위치 / 작성 원칙

| 원칙 | 적용 방식 |
|------|-----------|
| Markdown 콘텐츠와 HTML 대시보드 분리 | 본 문서는 기능 명세 Markdown이며, 추천 후보 대시보드는 별도 HTML 또는 UI 컴포넌트로 관리한다. |
| 프롬프트와 코드 분리 | 의도 파싱·추천 사유 생성 프롬프트는 코드에 직접 삽입하지 않고 문서 또는 프롬프트 폴더에 격리한다. |
| 기능별 파일 분리 | `A5` 단일 기능만 다루며 추천 후보의 상세 BUY/HOLD/SELL 판단은 A4로 연결한다. |
| 7대 표준 양식 준수 | 트리거, 전제조건, 입력, 처리 흐름, 출력, 예외 처리, 담당을 고정 순서로 작성한다. |
| 후보 스크리닝 LLM 금지 | 가격, 거래정지, 섹터, 유동성, 기본 재무 필터는 Python/SQL로 처리한다. |
| 비용 상한 명시 | A5 1회 실행당 LLM 호출은 최대 2회, 월 LLM 비용은 5만원 상한 내에서 제어한다. |
| MVP 범위 명확화 | MVP 추천 섹터는 반도체, 금융, 소비재 중심이며 후보 수는 5~10개로 제한한다. |

---

## 2. 기능 개요

종목 추천 기능은 “오늘 뭐 사지?”, “반도체 중에서 볼 만한 종목 추천해줘”처럼 대상 종목이 명확하지 않은 요청을 받아, 사용자의 투자성향과 관심 섹터에 맞는 후보 종목 5~10개를 카드 형태로 제공한다.

MVP에서는 추천을 “즉시 매수하라”는 의미로 제공하지 않고, 추가 분석을 시작할 후보 목록으로 제공한다. 각 후보 카드는 종목명, 섹터, 현재가, 등락률, 기본 재무/시세 근거, 추천 사유 한 줄, 후속 A4 분석 CTA로 구성한다.

---

## 3. 핵심 요약 표

| 항목 | 내용 |
|------|------|
| 기능명 | 종목 추천 |
| 기능 ID | `A5` |
| 목적 | 종목 미지정 사용자가 분석을 시작할 수 있도록 5~10개 후보 제공 |
| 주요 사용자 | 신규 사용자, 관심 섹터는 있으나 종목을 고르지 못한 사용자 |
| 주 트리거 | 자연어 요청에서 종목 미지정 의도 감지, 추천 메뉴 진입 |
| 전제조건 | `company`, `stock_price`, 기본 재무 데이터, 사용자 투자성향/관심 섹터 또는 기본값 |
| 주요 입력 | `user_query`, `user_id`, `risk_profile`, `interest_sectors`, `candidate_limit` |
| 메인 에이전트 | Curator Agent |
| 보조 에이전트 | Strategist, Guardrail, Quant Worker |
| 주요 DB | `users`, `holdings`, `company`, `stock_price`, `financial_data`, `analysis_cache`, `analysis_history` |
| 주요 출력 | 후보 종목 5~10개 카드, 추천 사유, 스크리닝 기준, 후속 A4 분석 CTA |
| LLM 비용 정책 | 의도 파싱 1회, 추천 사유 문장화 1회로 제한. 캐시 적중 시 0회 |
| 월 비용 상한 | 전체 서비스 월 LLM 비용 50,000원 초과 방지 |
| MVP 범위 | 반도체·금융·소비재 중심 국내 상장 종목 추천 |
| 제외 범위 | 글로벌 종목 추천, 자동매매, 개별 후보별 A1~A4 전체 선행 실행 |

---

## 4. A5. 종목 추천

### 4.1 트리거

- 사용자가 자연어 입력창에 종목명 없이 “추천해줘”, “오늘 볼 만한 종목”, “반도체 종목 알려줘”처럼 요청한다.
- 사용자가 메인 화면 또는 추천 페이지에서 `종목 추천 받기` 버튼을 클릭한다.
- 사용자가 B1 온보딩에서 투자성향과 관심 섹터를 입력한 뒤 첫 추천을 요청한다.
- 사용자가 B2 보유 종목 등록 이후 `내 포트폴리오와 겹치지 않는 후보 보기`를 클릭한다.
- 사용자가 A4 결과에서 `비슷한 후보 더 보기`를 클릭한다.

### 4.2 전제조건

| 조건 | 상세 |
|------|------|
| 사용자 요청 확보 | 자연어 요청 또는 추천 메뉴 진입 이벤트가 존재해야 한다. |
| 종목 미지정 판단 | 요청에 명확한 `stock_code` 또는 단일 종목명이 없거나, 사용자가 후보 추천을 명시해야 한다. |
| 사용자 프로필 | 로그인 사용자는 `users`에 투자성향과 관심 섹터가 저장되어 있으면 우선 사용한다. |
| 기본 추천 정책 | 관심 섹터가 없으면 MVP 3섹터인 반도체, 금융, 소비재를 균등하게 사용한다. |
| 종목 마스터 적재 | `company`에 국내 상장 종목, 시장구분, 섹터, 종목코드가 적재되어 있어야 한다. |
| 시세 데이터 적재 | `stock_price`에 최신 현재가, 등락률, 거래량, 거래정지 여부 판단 데이터가 있어야 한다. |
| 기본 재무 데이터 | `financial_data` 또는 `financial_statement`에 최소 최근 연간 재무 요약이 있으면 추천 품질을 높인다. |
| 비용 상태 확인 | 월 LLM 비용 집계가 5만원 상한을 초과하지 않아야 한다. 임계점 접근 시 LLM 추천 사유 생성을 제한한다. |
| 캐시 조회 가능 | 동일 사용자·동일 조건·동일 시장 기준의 최근 24시간 A5 추천 결과를 조회할 수 있어야 한다. |

### 4.3 입력

| 필드 | 타입 | 필수 | 출처 | 설명 |
|------|------|------|------|------|
| `user_query` | string/null | N | 자연어 입력 | 추천 의도, 섹터, 조건, 제외 요청 |
| `user_id` | string/null | N | 세션 | 사용자 성향, 관심 섹터, 보유 종목 조회용 |
| `risk_profile` | enum/null | N | `users`/UI | `conservative`, `balanced`, `aggressive` |
| `interest_sectors` | array/null | N | `users`/UI | 관심 섹터 목록. 없으면 MVP 3섹터 기본값 |
| `exclude_owned` | boolean | N | UI/기본값 | 보유 종목 제외 여부. 기본 `false` |
| `candidate_limit` | integer | N | UI/기본값 | 최종 후보 수. 기본 5개, 최대 10개 |
| `market_scope` | enum | N | 시스템 기본값 | `KOSPI`, `KOSDAQ`, `ALL_KR` |
| `min_liquidity` | integer/null | N | 시스템 기본값 | 최소 거래대금/거래량 필터 |
| `screening_profile` | enum | N | UI/기본값 | `value`, `growth`, `quality`, `balanced` |
| `force_refresh` | boolean | N | UI | 24시간 캐시를 무시하고 재추천할지 여부 |
| `company_rows` | array | Y | `company` | 추천 후보 종목 마스터 |
| `price_rows` | array | Y | `stock_price` | 현재가, 등락률, 거래량, 시가총액 |
| `financial_rows` | array/null | N | DB | PER, PBR, ROE, 매출성장률 계산용 재무 데이터 |

### 4.4 처리 흐름

1. **요청 및 의도 검증**
   - 자연어 요청이 있으면 Curator가 종목명, 섹터, 스타일, 제외 조건을 파싱한다.
   - 명확한 단일 종목이 감지되면 A5 추천 대신 B4 또는 A4 분석 플로우로 라우팅한다.
   - 종목 미지정 또는 후보 추천 의도가 확인되면 A5를 계속 진행한다.

2. **월 LLM 비용 상태 확인**
   - 운영 비용 집계에서 당월 LLM 사용액을 조회한다.
   - 30,000원 이상이면 추천 사유를 짧게 생성하고 후보 수를 기본 5개로 제한한다.
   - 40,000원 이상이면 의도 파싱 또는 추천 사유 생성 중 1회만 LLM을 사용한다.
   - 50,000원 이상이면 LLM 호출을 중지하고 UI 필터값과 규칙 기반 추천 사유만 사용한다.

3. **24시간 추천 캐시 우선 조회**
   - `analysis_cache` 또는 `analysis_history`에서 `feature_id = A5`, `user_id`, `query_intent_hash`, `sector_hash`, `screening_profile`, `market_data_version`이 같은 최근 24시간 결과를 조회한다.
   - 캐시가 있고 `force_refresh = false`이면 후보 스크리닝과 LLM 호출을 생략한다.
   - 캐시된 추천 후보를 UI에 반환하고 `최근 추천 재사용` 배지를 표시한다.

4. **사용자 프로필 및 포트폴리오 조회**
   - `users`에서 투자성향과 관심 섹터를 조회한다.
   - `holdings`에서 보유 종목을 조회해 `exclude_owned = true`이면 후보에서 제외한다.
   - 관심 섹터가 없으면 반도체, 금융, 소비재를 균등 배분한다.

5. **후보 Universe 구성**
   - `company`에서 국내 상장 종목을 조회한다.
   - MVP 범위에서는 반도체, 금융, 소비재 섹터를 우선한다.
   - 거래정지, 관리종목, 상장폐지 위험 플래그가 있는 종목은 제외한다.
   - `market_scope`에 따라 KOSPI/KOSDAQ/전체 국내 시장을 제한한다.

6. **시세·재무 기반 1차 스크리닝**
   - `stock_price`에서 현재가, 등락률, 거래량, 거래대금, 시가총액을 조회한다.
   - 유동성이 너무 낮거나 가격 데이터가 오래된 종목을 제외한다.
   - 가능한 경우 PER, PBR, ROE, 매출성장률, 부채비율을 Python으로 계산한다.
   - 계산 불가 지표는 결손 플래그를 달고 추천 점수에서 낮은 가중치를 적용한다.

7. **추천 점수 산출**
   - `value` 프로필은 낮은 PBR/PER, 양호한 ROE, 안정적 재무를 우선한다.
   - `growth` 프로필은 매출성장률, 최근 모멘텀, 거래대금 증가를 우선한다.
   - `quality` 프로필은 ROE, 영업이익률, 부채비율 안정성을 우선한다.
   - `balanced` 프로필은 가치, 성장, 품질 점수를 균형 배분한다.
   - 추천 점수는 Python 규칙 기반으로 계산하며 LLM이 점수를 임의 생성하지 않는다.

8. **섹터·포트폴리오 분산 조정**
   - 최종 후보가 특정 섹터에 과도하게 몰리지 않도록 섹터별 상한을 적용한다.
   - 사용자가 이미 많이 보유한 섹터는 점수를 낮추거나 후보 카드에 집중도 경고를 표시한다.
   - 후보 수는 5~10개로 제한해 후속 분석 비용이 폭발하지 않도록 한다.

9. **추천 사유 생성**
   - 비용 상태가 허용되면 LLM을 최대 1회 호출해 후보별 추천 사유 한 줄을 생성한다.
   - LLM 입력에는 후보별 계산 지표, 섹터, 가격 변화, 데이터 품질 플래그만 전달한다.
   - LLM은 새로운 사실이나 목표가를 만들지 않고, 계산된 근거를 쉬운 한국어로 변환한다.
   - 비용 임계점 초과 또는 LLM 실패 시 규칙 기반 템플릿 사유로 대체한다.

10. **Guardrail 검증**
    - “반드시 사야 한다”, “수익 보장”, “오늘 매수” 같은 직접 투자권유 표현을 차단한다.
    - 추천 후보는 분석 시작점이며 최종 판단은 A4에서 확인해야 한다는 안내를 포함한다.
    - 사용자 보유 정보가 외부 프롬프트에 노출되지 않도록 마스킹한다.

11. **RecommendationList 스키마 검증**
    - 최종 후보 수, 후보별 종목코드, 사유, 점수, 데이터 품질 플래그를 검증한다.
    - 후보가 0개이면 빈 리스트를 저장하지 않고 추천 불가 예외를 반환한다.

12. **결과 저장 및 반환**
    - 추천 결과를 `analysis_history`에 저장한다.
    - 최근 24시간 재사용을 위해 `analysis_cache`에 `feature_id`, `user_id`, `query_intent_hash`, `sector_hash`, `screening_profile`, `market_data_version`, `expires_at`을 저장한다.
    - UI에는 후보 카드, 스크리닝 기준, 제외된 조건, 후속 B4/A4 분석 CTA를 반환한다.

### 4.5 출력

| 출력 항목 | 타입 | 저장/렌더링 위치 | 설명 |
|-----------|------|------------------|------|
| `recommendation_title` | string | UI | 사용자 조건을 반영한 추천 목록 제목 |
| `candidate_cards` | array | UI/State/DB | 후보 5~10개 카드 |
| `candidate.stock_code` | string | UI/DB | 후보 종목 코드 |
| `candidate.company_name` | string | UI/DB | 후보 종목명 |
| `candidate.sector` | string | UI/DB | 섹터/업종 |
| `candidate.current_price` | integer/decimal | UI/DB | 기준일 현재가 |
| `candidate.change_rate` | decimal/null | UI/DB | 당일 또는 최근 기준 등락률 |
| `candidate.screening_score` | decimal | UI/DB | Python 규칙 기반 추천 점수 |
| `candidate.reason` | string | UI/DB | 추천 사유 한 줄 |
| `candidate.data_quality_flags` | array | UI/DB | 결손 지표, 낮은 유동성, 오래된 데이터 등 |
| `screening_summary` | object | UI/DB | 적용 섹터, 투자성향, 제외 조건, 후보 수 |
| `excluded_summary` | object | UI/DB | 거래정지, 데이터 부족, 보유 종목 제외 등 제외 사유 집계 |
| `next_action_cta` | object | UI | B4 기본 정보 보기, A4 종합 판단 받기 버튼 |
| `cache_status` | enum | UI/DB | `cache_hit`, `cache_miss`, `refreshed` |
| `RecommendationList` | object | LangGraph State/DB | 추천 후보 목록 및 후속 분석 입력 |

### 4.6 예외 처리

| 예외 상황 | 감지 조건 | 처리 방안 | 사용자 표시 |
|-----------|-----------|-----------|-------------|
| 종목이 명확히 지정됨 | 자연어에서 단일 종목명/코드 감지 | A5 중단, B4/A4로 라우팅 | `지정한 종목 분석으로 이동합니다.` |
| 사용자 관심 섹터 없음 | `interest_sectors` null | 반도체·금융·소비재 균등 추천 | `관심 섹터가 없어 기본 섹터로 추천합니다.` |
| MVP 외 섹터 요청 | 지원 섹터 외 요청 | 가능한 경우 전체 시장 검색, 아니면 기본 섹터 제안 | `해당 섹터는 추천 품질이 제한적입니다.` |
| 후보 0개 | 필터 후 유효 종목 없음 | 필터 완화 제안, 추천 결과 비움 | `현재 조건에 맞는 추천 가능 종목이 없습니다.` |
| 모든 후보 거래정지 | 후보 전부 거래정지/관리 플래그 | 추천 중단, 시장 데이터 재확인 안내 | `오늘 추천 가능한 종목이 없습니다.` |
| 시세 데이터 오래됨 | 최신 기준일이 정책 기준 초과 | 후보 제외 또는 오래된 데이터 플래그 표시 | `일부 후보는 시세 기준일이 오래되었습니다.` |
| 재무 데이터 부족 | PER/PBR/ROE 등 계산 불가 | 점수 가중치 축소, 후보 카드에 결손 표시 | `일부 재무 지표가 부족해 참고용입니다.` |
| 후보 수 과다 | 10개 초과 후보 생성 | 상위 점수와 섹터 분산 기준으로 10개 제한 | `상위 후보만 표시합니다.` |
| 포트폴리오 집중 위험 | 이미 보유 섹터/종목과 중복 높음 | 후보 점수 하향 또는 경고 표시 | `기존 보유와 겹치는 후보가 있습니다.` |
| LLM 비용 3만원 도달 | 당월 사용액 >= 30,000원 | 후보 5개 제한, 사유 문구 축소 | `비용 절감 모드로 추천 사유가 간결하게 제공됩니다.` |
| LLM 비용 4만원 도달 | 당월 사용액 >= 40,000원 | LLM 호출 1회 이하로 제한 | `비용 절감 정책에 따라 핵심 추천만 제공합니다.` |
| LLM 비용 5만원 도달 | 당월 사용액 >= 50,000원 | LLM 호출 중지, 규칙 기반 사유 사용 | `월 비용 상한 도달로 AI 추천 사유 생성을 중지했습니다.` |
| LLM 실패/타임아웃 | 호출 실패 또는 제한 시간 초과 | 템플릿 추천 사유로 대체 | `AI 추천 사유 생성에 실패해 기본 설명을 표시합니다.` |
| Guardrail 차단 | 직접 매수 지시, 수익 보장 표현 감지 | 문구 수정, 후보는 유지 | `일부 표현은 안전 정책에 따라 조정되었습니다.` |
| Pydantic 검증 실패 | `RecommendationList` 필수 필드 누락 | 저장 중단, 재시도 버튼 제공 | `추천 결과 검증에 실패했습니다.` |
| DB 저장 실패 | `analysis_history`/`analysis_cache` insert 실패 | UI 반환은 유지, 저장 실패 로깅 | `추천 결과 저장에 실패했습니다.` |

### 4.7 담당

| 영역 | 메인 담당 | 보조 담당 | 관련 테이블/모듈 | 설명 |
|------|-----------|-----------|------------------|------|
| 의도 파싱 | Curator Agent | Guardrail | LLM Gateway, Prompt Store | 종목 미지정 추천 의도와 조건 파악 |
| 사용자 프로필 조회 | Curator Agent | Backend API | `users`, `holdings` | 투자성향, 관심 섹터, 보유 종목 조회 |
| 후보 Universe 구성 | Curator Agent | Data Loader | `company`, `stock_price` | 국내 상장 종목과 MVP 섹터 후보 구성 |
| 스크리닝 계산 | Curator Agent | Quant Worker | `financial_data`, `financial_statement`, `stock_price` | 가치/성장/품질 점수 계산 |
| 추천 사유 생성 | Curator Agent | Guardrail | LLM Gateway | 후보별 한 줄 사유 문장화 |
| 비용 제어 | Guardrail | Ops Monitor | `llm_cost_log` 또는 운영 집계 | 월 5만원 상한, 임계점별 호출 제한 |
| 캐시 관리 | Curator Agent | Backend API | `analysis_cache`, `analysis_history` | 24시간 캐시 조회, 저장, 만료 관리 |
| 후속 분석 연결 | Strategist | Curator Agent | LangGraph State | 후보 클릭 시 B4/A4로 연결 |
| 사용자 화면 | UI Controller | Curator Agent | Streamlit/Frontend | 후보 카드, 필터 요약, CTA 렌더링 |

---

## 5. 기능-에이전트-DB-LLM 호출 매핑

| 단계 | 담당 에이전트 | DB/도구 | LLM 호출 | 비고 |
|------|---------------|---------|----------|------|
| 의도 파싱 | Curator Agent | LLM Gateway | 최대 1회 | 비용 4만원 이상이면 UI 필터값 우선 |
| 캐시 조회 | Curator Agent | `analysis_cache`, `analysis_history` | 0회 | 24시간 내 동일 조건 결과 우선 |
| 사용자 프로필 조회 | Curator Agent | `users`, `holdings` | 0회 | 성향/섹터/보유 여부 |
| 후보 Universe 구성 | Curator Agent | `company`, `stock_price` | 0회 | 국내 MVP 섹터 중심 |
| 추천 점수 계산 | Curator Agent | Python scoring module | 0회 | 수치 계산은 LLM 금지 |
| 추천 사유 생성 | Curator Agent + Guardrail | LLM Gateway | 최대 1회 | 후보 5~10개 한 줄 사유 |
| 안전 검증 | Guardrail | 정규식/정책 필터 | 0회 | 직접 투자권유 표현 차단 |
| 이력 저장 | Curator Agent | `analysis_history`, `analysis_cache` | 0회 | 추천 결과 재사용 |

---

## 6. KPI / 비용 상한 / 운영 기준

| 지표 | 목표 | 측정 방식 |
|------|------|-----------|
| 추천 결과 응답 시간 | 30초 이내 | 트리거부터 후보 카드 렌더링 완료까지 |
| 캐시 적중 응답 시간 | 5초 이내 | 24시간 캐시 존재 시 UI 표시 완료까지 |
| LLM 호출 수 | A5 실행당 최대 2회 | LLM Gateway 호출 로그 |
| 월 LLM 비용 | 50,000원 이하 | 운영 비용 집계 |
| 후보 수 | 5~10개 | `RecommendationList` 검증 |
| 후보 데이터 완성도 | 후보 80% 이상 핵심 지표 3개 이상 보유 | 스크리닝 로그 |
| 거래정지 후보 노출 | 0건 | 후보 필터 검증 |
| 직접 매수 표현 | 0건 | Guardrail 검증 |
| 후속 분석 클릭률 | 추천 카드 클릭 또는 A4 CTA 클릭 | UI 이벤트 로그 |
| 스키마 검증 성공률 | 99% 이상 | `RecommendationList` 검증 로그 |

---

## 7. 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|-----------|
| 2026-05-23 | v1.1 | A5. 종목 추천 기능별 상세 명세서 초안 작성 |

