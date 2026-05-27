# User Intake Multi-Agent TODO

| 항목 | 내용 |
|------|------|
| 작성일 | 2026-05-27 |
| 담당 범위 | 유저 데이터 수집, 유저 질문 정규화, 유저 포트폴리오 초입 단계 |
| 관련 문서 | `docs/architecture/multi_agent_architecture.md`, `docs/architecture/erd.md`, `docs/functional-spec/basic/B1_signup_login_spec_v0.3.md`, `docs/functional-spec/basic/B2_holdings_manage_spec_v0.4.md`, `docs/functional-spec/basic/B5_portfolio_bulk_advice_spec_v0.2.md` |
| 현재 구현 기준 | Phase 1 mock pipeline |
| 목표 구현 기준 | 금융 멀티 에이전트가 신뢰할 수 있는 사용자 컨텍스트 계약 구축 |

---

## 1. 방향성

이 작업의 목표는 단순히 입력폼을 만드는 것이 아니라, 멀티 에이전트가 공통으로 신뢰할 수 있는 사용자 컨텍스트를 만드는 것이다.

우리 프로젝트에서는 다음 원칙을 따른다.

| 원칙 | 설명 |
|------|------|
| 사용자 입력과 시스템 계산 분리 | 사용자가 직접 입력한 값과 가격/비중/수익률 같은 계산값을 구분한다. |
| 객관 분석과 개인화 해석 분리 | Quant, Qual, Competitor는 객관 evidence를 만들고, Strategist가 사용자 성향을 반영한다. |
| 금융 안전성 우선 | 투자 권유, 수익 보장, 과도한 매수/매도 단정 표현을 피한다. |
| 작은 단위로 검증 | DB 연결 전에 schema와 Streamlit mock flow부터 검증한다. |
| 추적 가능성 확보 | 향후 `analysis_history`, `evidence_log`, `agent_run_log`로 이어질 수 있게 입력 계약을 남긴다. |

---

## 2. 큰 계획

### Phase 0. 현재 구조 이해와 계약 정리

- [x] 현재 Phase 1 pipeline 구조 파악
- [x] `UserProfile`, `Portfolio`, `Holding`, `AgentState` 현재 필드 파악
- [x] 관련 기능 명세 `B1`, `B2`, `B5` 확인
- [x] 사용자 초입에서 필요한 최종 입력 계약 초안 확정
- [x] `users`, `holdings`, `analysis_history` 책임 범위 공유용 초안 작성
- [ ] 팀원과 `users`, `holdings`, `analysis_history` 책임 범위 실제 공유 및 합의

### Phase 0 입력 계약 초안

Phase 0에서는 DB schema를 바로 변경하지 않고, agent pipeline이 기대하는 입력 계약을 먼저 확정한다. 1차 구현은 Pydantic schema와 Streamlit mock 입력으로 검증한다.

#### `UserProfile`

사용자의 투자 성향과 제약 조건을 담는다. Strategist가 개인화 판단을 할 때 가장 강하게 사용한다.

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `user_id` | string | 필수 | 현재 사용자 식별자. MVP에서는 demo id 허용 |
| `risk_tolerance` | enum | 필수 | `low`, `medium`, `high` |
| `investment_horizon_months` | int | 필수 | 투자 기간. 기존 필드 유지 |
| `target_return_rate` | float | 선택 | 목표 수익률. 예: `0.1`은 10% |
| `max_drawdown_tolerance` | float | 선택 | 허용 손실률. 예: `-0.1`은 -10% |
| `investment_goal` | enum/string | 선택 | 안정적 자산관리, 중장기 성장, 단기 수익, 배당 등 |
| `experience_level` | enum/string | 선택 | `beginner`, `intermediate`, `advanced` |
| `cash_source` | string | 선택 | 기존 필드 유지. 여유자금, 생활자금 등 |
| `preferred_sectors` | list[string] | 선택 | MVP 기본값은 반도체/금융 |
| `excluded_sectors` | list[string] | 선택 | 사용자가 피하고 싶은 산업 |
| `liquidity_need_level` | enum/string | 선택 | `low`, `medium`, `high` |

#### `Holding`

사용자가 직접 입력한 보유 종목 원장과 시스템 계산값을 분리한다.

| 필드 | 타입 | 필수 | 입력 주체 | 설명 |
|------|------|------|-----------|------|
| `stock_code` | string | 필수 | 사용자/검색 | KRX 6자리 종목코드 |
| `corp_name` | string | 필수 | 검색/DB | 종목명 |
| `sector` | string | 선택 | DB | 산업. MVP는 반도체/금융 중심 |
| `avg_price` | int | 선택 | 사용자 | 평균 매수가 |
| `qty` | int | 선택 | 사용자 | 보유 수량 |
| `bought_at` | date/string | 선택 | 사용자 | 대표 매수일 |
| `current_price` | int | 선택 | 시스템 | 최근 가격. 입력값이 아니라 조회/계산값 |
| `weight` | float | 선택 | 시스템 | 포트폴리오 평가금액 기준 비중 |

#### `Portfolio`

보유 종목 목록과 현금 비중을 담는다. 평가금액, 수익률, 섹터 비중은 helper 또는 service에서 계산한다.

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `holdings` | list[Holding] | 필수 | 사용자 보유 종목 목록 |
| `cash_weight` | float | 필수 | 현금 비중. 0~1 |
| `as_of_date` | date/string | 선택 | 분석 기준일 |

#### `UserRequest`

사용자 자연어 질문을 agent가 처리하기 쉬운 분석 요청으로 정규화한다. 기존 `AgentState.user_query`는 호환을 위해 유지하되, 이후 `user_request`를 추가하는 방향을 우선 검토한다.

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `raw_query` | string | 필수 | 사용자 원문 질문 |
| `intent` | enum/string | 선택 | 보유 종목 점검, 신규 추천, 리스크 점검, 매도 판단, 포트폴리오 전체 점검 |
| `target_stock_code` | string | 선택 | 질문에서 확정된 분석 대상 종목 |
| `target_corp_name` | string | 선택 | 분석 대상 종목명 |
| `analysis_scope` | enum | 선택 | `single_stock`, `portfolio`, `sector` |
| `urgency_reason` | enum/string | 선택 | 급등, 급락, 실적, 뉴스, 일반점검 |
| `requested_depth` | enum | 선택 | `summary`, `standard`, `deep` |

### Phase 0 테이블 책임 범위 초안

DB schema는 팀 합의 후 별도 PR로 진행한다. Phase 0 기준 책임 범위는 다음처럼 나눈다.

| 테이블 | 책임 | 1차 담당 제안 | 비고 |
|--------|------|---------------|------|
| `users` | 회원 식별, 투자성향, 관심 섹터, 투자 제약 저장 | 유저 초입 담당 | 비밀번호/인증 구현은 B1 범위라 별도 논의 필요 |
| `holdings` | 사용자 보유 종목 원장 저장 | 유저 초입 담당 | `company`, `stock_price`와 조인해 계산값 생성 |
| `analysis_history` | 사용자에게 노출한 최종 분석 결과 저장 | pipeline/Strategist 담당과 협업 | 캐시, 재현성, 감사 로그와 연결 |
| `agent_run_log` | agent별 실행 상태, 오류, 비용 추적 | pipeline/운영 담당과 협업 | 아직 문서상 제안 단계 |
| `evidence_log` | 최종 판단에 사용된 출처와 계산 근거 저장 | RAG/Quant/Qual 담당과 협업 | 금융 explainability를 위해 필요 |

### Phase 1. UserProfile 확장

- [x] `risk_tolerance` 기준 확정: `low`, `medium`, `high`
- [x] `investment_horizon_months` 유지 또는 단기/중기/장기 enum 변환 여부 결정
- [x] `target_return_rate` 추가
- [x] `max_drawdown_tolerance` 추가
- [x] `investment_goal` 추가
- [x] `experience_level` 추가
- [x] `preferred_sectors`를 MVP 산업 범위에 맞게 정리: 반도체, 금융
- [x] `excluded_sectors` 필요 여부 검토
- [x] schema 변경에 맞춘 테스트 추가

### Phase 2. Portfolio / Holding 확장

- [x] `Holding`에 `qty` 추가
- [x] `Holding`에 `sector` 추가
- [x] `Holding`에 `bought_at` 추가
- [x] `Holding`에 `current_price`를 계산/조회값으로 둘지 검토
- [x] `avg_price * qty` 기반 `cost_basis` 계산 helper 검토
- [x] `current_price * qty` 기반 `market_value` 계산 helper 검토
- [x] 포트폴리오 내 `weight`를 입력값으로 둘지 계산값으로 둘지 결정
- [x] 섹터별 비중 계산 helper 검토

### Phase 3. UserRequest 도입

- [x] `raw_query` 보관
- [x] `intent` 후보 정의: 보유 종목 점검, 신규 추천, 리스크 점검, 매도 판단, 포트폴리오 전체 점검
- [x] `target_stock_code` / `target_corp_name` 필드 정의
- [x] `analysis_scope` 정의: `single_stock`, `portfolio`, `sector`
- [x] `urgency_reason` 정의: 급등, 급락, 실적, 뉴스, 일반점검
- [x] `requested_depth` 정의: `summary`, `standard`, `deep`
- [x] 기존 `AgentState.user_query`와의 호환 방식 결정

### Phase 4. Streamlit 초입 UI 개선

- [ ] 사이드바의 MVP 사용자 데이터 입력 확장
- [ ] 투자성향 설문형 입력 추가
- [ ] 관심 섹터를 반도체/금융 중심으로 제한
- [ ] 보유 종목 수동 입력 UI 추가
- [ ] 현금 비중 입력 유지
- [ ] 질문 입력과 분석 실행 흐름 유지
- [ ] 입력값 검증 메시지 추가

### Phase 5. Curator 개선

- [ ] 질문에서 종목명/종목코드 추출
- [ ] 보유 종목 안에서 먼저 target 매칭
- [ ] 질문에 종목이 없으면 포트폴리오 전체 점검으로 분류
- [ ] 선호 섹터 기반 후보 추천
- [ ] MVP 지원 산업 밖이면 warning 반환
- [ ] 애매한 질문은 candidates로 넘기고 임의 확정하지 않기

### Phase 6. Strategist 개인화 강화

- [ ] 투자성향별 suitability 계산 기준 추가
- [ ] 보유 비중이 높은 경우 안정형 사용자에게 경고 강화
- [ ] 급등/급락 이벤트와 투자성향 불일치 시 next_actions 차별화
- [ ] 현금 비중과 투자 기간을 함께 반영
- [ ] 최종 signal과 suitability를 분리해서 설명
- [ ] Guardrail 문구와 충돌하지 않도록 표현 정리

### Phase 7. DB 연결 준비

- [ ] `users` 테이블 최종 필드 검토
- [ ] `holdings` 테이블 최종 필드 검토
- [ ] `analysis_history` 저장 범위 검토
- [ ] 기존 `db/init/001_create_raw_tables.sql`와 문서 ERD 차이 정리
- [ ] DB schema 변경은 팀 합의 후 별도 PR로 진행

---

## 3. 작은 계획: 1차 PR 범위

1차 PR은 DB를 건드리지 않고, schema와 mock UI/pipeline을 단단하게 만드는 범위로 제한한다.

예상 PR 제목:

```text
feat: add user intake and portfolio context schema
```

포함할 작업:

- [ ] `src/stock_agent/schemas/analysis.py`의 `UserProfile` 확장
- [ ] `src/stock_agent/schemas/analysis.py`의 `Holding`, `Portfolio` 확장
- [ ] 필요하면 `UserRequest` schema 추가
- [ ] `streamlit_app.py`의 사용자 입력 UI 개선
- [ ] `src/stock_agent/agents/curator.py`가 보유 종목 기준으로 target을 찾도록 개선
- [ ] `src/stock_agent/agents/strategist.py`가 투자성향과 보유 비중을 더 명확히 반영하도록 개선
- [ ] `tests/test_phase1_pipeline.py`에 schema/curator/strategist 테스트 추가

완료 기준:

- [ ] `PYTHONPATH=src python3 -m pytest -q -s` 통과
- [ ] 기존 Phase 1 mock pipeline 동작 유지
- [ ] 삼성전자 질문이 기존처럼 분석됨
- [ ] 종목 미지정 질문에서 candidates 또는 포트폴리오 점검 intent가 반환됨
- [ ] 안정형 사용자 + 높은 보유 비중 케이스에서 suitability가 보수적으로 계산됨

---

## 4. 추천 투자성향 설문 초안

MVP에서는 질문을 너무 길게 만들지 않는다. 6~8개 문항으로 시작한다.

| 질문 | 저장 필드 | 예시 선택지 |
|------|-----------|-------------|
| 투자 기간은 어느 정도인가요? | `investment_horizon_months` | 3개월, 6개월, 12개월, 36개월 |
| 목표 수익률은 어느 정도인가요? | `target_return_rate` | 5%, 10%, 20%, 직접 입력 |
| 감내 가능한 손실 폭은 어느 정도인가요? | `max_drawdown_tolerance` | -5%, -10%, -20%, 직접 입력 |
| 한 달 사이 보유 종목이 10% 하락하면 어떻게 하시나요? | `risk_tolerance` | 매도 검토, 관망, 추가 매수 검토 |
| 투자 목적은 무엇인가요? | `investment_goal` | 안정적 자산관리, 중장기 성장, 단기 수익, 배당 |
| 투자 경험은 어느 정도인가요? | `experience_level` | 초보, 중급, 고급 |
| 관심 산업은 무엇인가요? | `preferred_sectors` | 반도체, 금융 |
| 당장 써야 할 현금이 있나요? | `liquidity_need_level` | 낮음, 보통, 높음 |

---

## 5. 리스크와 주의점

| 리스크 | 대응 |
|--------|------|
| 사용자 성향이 과도하게 단순화됨 | 설문 결과와 직접 선택값을 함께 저장한다. |
| LLM이 수치를 만들어낼 위험 | 수익률, 비중, valuation은 Python/SQL 계산값만 사용한다. |
| 투자 권유처럼 보일 위험 | `분석 신호`, `검토`, `주의`, `가능성` 중심 표현을 사용한다. |
| DB schema를 성급히 바꿀 위험 | 1차 PR에서는 schema/mock flow만 변경하고 DB는 팀 합의 후 진행한다. |
| 산업 범위가 넓어질 위험 | MVP는 반도체/금융으로 제한하고 warning을 명확히 표시한다. |

---

## 6. 변경 이력

| 날짜 | 변경 내용 |
|------|-----------|
| 2026-05-27 | 유저 초입 담당 범위의 큰 계획/작은 계획/TODO 초안 작성 |
