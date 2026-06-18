# 기능 명세서 v1.0 - A4. BUY/HOLD/SELL 권유

| 항목 | 값 |
|------|-----|
| 작성자 | PM |
| 작성일 | 2026-05-23 |
| 버전 | v1.0 |
| 상위 문서 | `docs/prd/PRD_v0.6.md` |
| 참조 문서 | `docs/functional-spec/overview/functional_spec_all_features_v0.1.md`, `docs/functional-spec/advanced/A1_valuation_5y_spec_v0.7.md`, `docs/functional-spec/advanced/A2_industry_qualitative_spec_v0.8.md`, `docs/functional-spec/advanced/A3_peer_comparison_spec_v1.0.md`, `docs/functional-spec/basic/B2_holdings_manage_spec_v0.4.md`, `docs/architecture/system_flow.md`, `docs/architecture/erd.md`, `docs/operations/llm_cost_guide.md` |
| 대상 사용자 | 개인투자자, PM, 개발팀, 운영팀 |
| 기능 ID | `A4` |
| 기능명 | BUY/HOLD/SELL 권유 |

---

## 0. 문서 메타 정보

본 문서는 PRD 기준 고급 기능 `A4. BUY/HOLD/SELL 권유`의 상세 기능 명세서다. 기존 통합 초안의 7대 표준 양식인 **트리거 / 전제조건 / 입력 / 처리 흐름 / 출력 / 예외 처리 / 담당** 순서를 유지하고, Strategist & Synthesizer가 A1/A2/A3 및 포트폴리오 정보를 종합해 사용자에게 근거 있는 행동 방향을 제시하는 흐름을 구체화한다.

`A4`는 프로젝트의 핵심 사용자 가치에 가장 가까운 기능이다. 다만 실제 주문 집행이나 법적 의미의 투자자문이 아니므로 모든 출력은 “교육용 참고 정보”로 제한하며, Guardrail이 직접적·확정적 투자권유 표현을 차단한다. 결론은 BUY/HOLD/SELL 형식으로 제공하되, 반드시 신뢰도, 포트폴리오 적합도, WHAT/HOW MUCH/WHY/RISK 근거를 함께 표시한다.

---

## 1. 문서 위치 / 작성 원칙

| 원칙 | 적용 방식 |
|------|-----------|
| Markdown 콘텐츠와 HTML 대시보드 분리 | 본 문서는 기능 명세 Markdown이며, 권유 결과 대시보드는 별도 HTML 또는 UI 컴포넌트로 관리한다. |
| 프롬프트와 코드 분리 | Strategist 종합 프롬프트, 자체 검증 프롬프트, Guardrail 프롬프트는 코드에 직접 삽입하지 않고 문서 또는 프롬프트 폴더에 격리한다. |
| 기능별 파일 분리 | `A4` 단일 기능만 다루며 A1/A2/A3의 산출물 생성 과정은 참조만 한다. |
| 7대 표준 양식 준수 | 트리거, 전제조건, 입력, 처리 흐름, 출력, 예외 처리, 담당을 고정 순서로 작성한다. |
| 법적 안전성 | 실제 주문, 자동매매, 개인 맞춤 자문처럼 오해될 표현을 금지하고 책임 고지를 포함한다. |
| 비용 상한 명시 | A4 1회 실행당 LLM 호출은 최대 3회, 월 LLM 비용은 5만원 상한 내에서 제어한다. |
| 하드 룰 우선 | 신뢰도·포트 적합도·손실 시나리오에 대한 강제 다운그레이드 규칙은 LLM 판단보다 우선한다. |

---

## 2. 기능 개요

BUY/HOLD/SELL 권유 기능은 특정 종목에 대해 정량 가치평가, 정성 뉴스/공시 분석, 동종업계 비교, 사용자 보유 포트폴리오 맥락을 종합해 한 줄 결론과 근거 카드를 제공한다.

MVP 화면은 `BUY 78% / 적합도 ★★★★ / 현금 30% 중 5%p 매수 검토` 같은 Tier 1 결론과, 펼쳐볼 수 있는 WHAT, HOW MUCH, WHY, RISK 근거 섹션으로 구성한다. 결론은 투자 판단 보조 정보이며 실제 주문 실행이나 수익 보장을 의미하지 않는다.

---

## 3. 핵심 요약 표

| 항목 | 내용 |
|------|------|
| 기능명 | BUY/HOLD/SELL 권유 |
| 기능 ID | `A4` |
| 목적 | A1/A2/A3/포트폴리오 결과를 종합해 근거 있는 행동 방향 제시 |
| 주요 사용자 | 결정을 내려야 하는 개인투자자, PB 리포트 생성 사용자 |
| 주 트리거 | B4/A1/A2/A3 화면의 `종합 판단 받기`, A4 직접 실행 |
| 전제조건 | `QuantReport`, `QualReport`, `CompetitorReport` 중 최소 핵심 입력 확보 |
| 주요 입력 | `stock_code`, `user_id`, `QuantReport`, `QualReport`, `CompetitorReport`, 보유 종목/현금 비중 |
| 메인 에이전트 | Strategist & Synthesizer |
| 보조 에이전트 | Quant Worker, Qual Worker, Competitor Agent, Guardrail, Curator |
| 주요 DB | `users`, `holdings`, `analysis_history`, `analysis_cache`, `company`, `stock_price` |
| 주요 출력 | BUY/HOLD/SELL, 신뢰도, 포트 적합도, 권유 비중, 4대 근거, `ActionRecommendation` |
| LLM 비용 정책 | 24시간 내 동일 조건 A4 결과 캐시 우선, 캐시 미스 시 최대 3회 |
| 월 비용 상한 | 전체 서비스 월 LLM 비용 50,000원 초과 방지 |
| 필수 하드 룰 | 신뢰도 60% 미만 BUY 금지, 포트 적합도 1점 BUY 금지, 모든 시나리오 손실 예상 시 매수 비추천 |
| MVP 범위 | 종목 1개에 대한 교육용 참고 결론과 근거 제공 |
| 제외 범위 | 주문 실행, 자동매매, 세무/법률 자문, 권유 유효기간 알림 |

---

## 4. A4. BUY/HOLD/SELL 권유

### 4.1 트리거

- 사용자가 B4 종목 기본 정보 화면에서 `종합 판단 받기`를 클릭한다.
- 사용자가 A1 밸류에이션, A2 정성 분석, A3 Peer 비교 결과 화면에서 `BUY/HOLD/SELL 보기`를 클릭한다.
- 사용자가 B5 포트폴리오 일괄 안내 결과에서 특정 종목의 `행동 방향 보기`를 클릭한다.
- 사용자가 보유 종목 목록에서 특정 종목의 `매수/보유/매도 판단`을 요청한다.
- 사용자가 기존 A4 분석 이력에서 `최신 데이터로 다시 판단`을 클릭한다.

### 4.2 전제조건

| 조건 | 상세 |
|------|------|
| 종목 코드 확정 | `stock_code`는 6자리 문자열이며 `company` 테이블에 존재해야 한다. |
| 분석 입력 확보 | A1 `QuantReport`, A2 `QualReport`, A3 `CompetitorReport` 중 최소 2개 이상이 있거나 즉시 생성 가능해야 한다. |
| 정량 핵심값 존재 | 현재가, 적정가 또는 안전마진 중 최소 1개 이상이 있어야 한다. |
| 포트폴리오 맥락 | 로그인 사용자는 `holdings`에서 보유 여부, 평가금액, 비중, 현금 비중을 조회할 수 있어야 한다. |
| 비회원 처리 정책 | 비회원 또는 포트폴리오 미등록 사용자는 일반 종목 판단으로 진행하되 포트 적합도는 제한 표시한다. |
| 비용 상태 확인 | 월 LLM 비용 집계가 5만원 상한을 초과하지 않아야 한다. 임계점 접근 시 자체 검증/설명 호출을 축소한다. |
| 캐시 조회 가능 | 동일 종목·동일 사용자 포트폴리오·동일 분석 입력 기준의 최근 24시간 A4 결과를 조회할 수 있어야 한다. |
| Guardrail 준비 | 투자권유 아님 고지, 단정 표현 차단, PII 마스킹, 금지 표현 필터가 동작해야 한다. |

### 4.3 입력

| 필드 | 타입 | 필수 | 출처 | 설명 |
|------|------|------|------|------|
| `stock_code` | string | Y | B4/A1/A2/A3/B5 | 판단 대상 종목 코드. 6자리 숫자 문자열 |
| `user_id` | string/null | N | 세션 | 포트폴리오 조회 및 이력 저장용 사용자 ID |
| `quant_report` | object/null | N | A1/DB | 적정가, 안전마진, 시나리오, DCF/Multiple 결과 |
| `qual_report` | object/null | N | A2/DB | 호재/악재, 공시 리스크, 뉴스 타임라인 |
| `competitor_report` | object/null | N | A3/DB | Peer 대비 위치, 비교 지표, 데이터 품질 |
| `holding_snapshot` | object/null | N | `holdings` | 보유 수량, 평균단가, 평가금액, 비중, 평가손익 |
| `cash_ratio` | decimal/null | N | 사용자 입력/포트폴리오 | 현금 비중. 없으면 권유 비중 산출 제한 |
| `risk_profile` | enum/null | N | 사용자 설정 | `conservative`, `balanced`, `aggressive` |
| `decision_mode` | enum | N | UI/기본값 | `quick`, `standard`, `detailed` |
| `force_refresh` | boolean | N | UI | 24시간 캐시를 무시하고 재판단할지 여부 |
| `cost_state` | object | Y | 운영 집계 | 당월 LLM 사용액, 임계점 상태 |

### 4.4 처리 흐름

1. **요청 검증**
   - `stock_code` 형식과 `company` 존재 여부를 확인한다.
   - `user_id`가 있으면 사용자 세션과 권한을 확인한다.
   - 필수 입력이 부족하면 A1/A2/A3 중 필요한 선행 분석을 호출하거나 제한 판단 모드로 전환한다.

2. **월 LLM 비용 상태 확인**
   - 운영 비용 집계에서 당월 LLM 사용액을 조회한다.
   - 30,000원 이상이면 설명 길이와 자체 검증 반복을 축소한다.
   - 40,000원 이상이면 LLM 호출을 1회로 제한하고 규칙 기반 점수 계산을 우선한다.
   - 50,000원 이상이면 LLM 호출을 중지하고 Python 규칙 기반 결론과 템플릿 근거만 제공한다.

3. **24시간 권유 캐시 우선 조회**
   - `analysis_cache` 또는 `analysis_history`에서 `feature_id = A4`, `stock_code`, `user_id`, `input_report_hash`, `portfolio_hash`가 같은 최근 24시간 결과를 조회한다.
   - 캐시가 있고 `force_refresh = false`이면 Strategist LLM 호출과 Guardrail LLM 호출을 생략한다.
   - 캐시된 `ActionRecommendation`을 UI에 반환하고 `최근 종합 판단 재사용` 배지를 표시한다.

4. **선행 분석 결과 수집**
   - A1 `QuantReport`, A2 `QualReport`, A3 `CompetitorReport`를 LangGraph State 또는 `analysis_history`에서 조회한다.
   - 누락된 보고서가 있으면 비동기 또는 순차로 생성한다.
   - 60초 응답 목표를 넘길 위험이 있으면 먼저 가용 보고서 기반 제한 결론을 제공하고, 나머지는 후속 업데이트로 처리한다.

5. **포트폴리오 컨텍스트 조회**
   - `holdings`에서 사용자의 대상 종목 보유 여부, 수량, 평균단가, 평가금액, 전체 포트폴리오 비중을 조회한다.
   - 현금 비중이 없으면 권유 비중 대신 “비중 산출 제한”을 표시한다.
   - 보유 종목이 아니면 신규 편입 관점, 보유 중이면 추가매수/보유/축소 관점으로 판단한다.

6. **규칙 기반 1차 점수 계산**
   - 정량 점수: 안전마진, 시나리오별 적정가, 현재가 괴리율을 반영한다.
   - 정성 점수: 호재/악재 이벤트, 공시 리스크, Faithfulness/출처 품질을 반영한다.
   - Peer 점수: PER/PBR/ROE/성장률의 Peer 분위수를 반영한다.
   - 포트 적합도: 기존 비중, 현금 비중, 집중도, 평가손익, 사용자 위험성향을 반영한다.
   - 모든 점수 계산은 Python 규칙으로 수행하고 LLM이 임의 수치를 만들지 않는다.

7. **Strategist 1차 결론 생성**
   - 비용 상태가 허용되면 Strategist가 4개 입력을 종합해 1차 `BUY`, `HOLD`, `SELL` 결론을 생성한다.
   - 결론에는 신뢰도, 적합도 별점, 권유 비중, 핵심 근거 4개가 포함되어야 한다.
   - LLM 입력에는 이미 계산된 점수와 보고서 요약만 전달한다.

8. **하드 룰 적용**
   - 1차 결론이 BUY인데 신뢰도 60% 미만이면 HOLD로 강제 다운그레이드한다.
   - 1차 결론이 BUY인데 포트폴리오 적합도 1점이면 HOLD로 강제 다운그레이드한다.
   - 모든 시나리오에서 손실 또는 음의 안전마진이 예상되면 `매수 비추천` 또는 SELL 후보로 표시한다.
   - 선행 보고서가 2개 미만이면 BUY를 금지하고 HOLD 또는 판단 보류로 제한한다.
   - 위 규칙은 LLM 판단보다 항상 우선한다.

9. **WHAT/HOW MUCH/WHY/RISK 근거 구성**
   - WHAT: 최종 행동 방향과 신뢰도.
   - HOW MUCH: 적정가, 안전마진, 권유 비중 또는 비중 산출 제한 사유.
   - WHY: 정량, 정성, Peer, 포트폴리오 적합도 근거.
   - RISK: 데이터 결손, 공시 리스크, Peer 부족, 가격 변동성, 모델 한계.

10. **자체 검증 및 반론 생성**
    - 비용 상태가 허용되면 Strategist가 자체 Critic 단계로 결론의 약점을 점검한다.
    - 반론이 강하면 신뢰도를 낮추거나 HOLD로 보수화한다.
    - PRD의 Critic Agent 분리 제외 원칙에 따라 별도 Critic Agent를 만들지 않고 Strategist 내부 단계로 처리한다.

11. **Guardrail 최종 검증**
    - 직접적인 주문 지시, 수익 보장, 과장 표현, 근거 없는 단정을 차단한다.
    - “투자 권유가 아닌 교육용 참고 정보” 고지를 결과 하단에 포함한다.
    - 사용자 PII, 보유 금액 등 민감 정보가 외부 프롬프트에 노출되지 않도록 마스킹한다.

12. **ActionRecommendation 스키마 검증**
    - `ActionRecommendation` 스키마로 최종 결론, 신뢰도, 적합도, 권유 비중, 근거, 리스크, 하드 룰 적용 이력을 검증한다.
    - 결론과 근거가 모순되거나 하드 룰 위반이 있으면 저장을 중단하고 HOLD로 보수화한다.

13. **결과 저장 및 반환**
    - `ActionRecommendation`을 `analysis_history`에 저장한다.
    - 최근 24시간 재사용을 위해 `analysis_cache`에 `feature_id`, `stock_code`, `user_id`, `input_report_hash`, `portfolio_hash`, `expires_at`을 저장한다.
    - UI에는 Tier 1 한 줄 결론, 근거 카드, 리스크, 책임 고지, PB 리포트 다운로드 CTA를 반환한다.

### 4.5 출력

| 출력 항목 | 타입 | 저장/렌더링 위치 | 설명 |
|-----------|------|------------------|------|
| `action` | enum | UI/State/DB | `BUY`, `HOLD`, `SELL`, `WATCH`, `INSUFFICIENT_DATA` |
| `confidence_score` | integer | UI/State/DB | 0~100 신뢰도 |
| `portfolio_fit_score` | integer | UI/State/DB | 1~5 별점 적합도 |
| `headline` | string | UI | Tier 1 한 줄 결론 |
| `suggested_allocation_delta` | decimal/null | UI/DB | 현금 또는 포트폴리오 대비 권유 비중 변화 |
| `fair_value_reference` | object/null | UI/State | A1 적정가, 현재가, 안전마진 |
| `what_card` | object | UI/DB | 최종 행동 방향과 신뢰도 근거 |
| `how_much_card` | object | UI/DB | 적정가, 안전마진, 비중 제안 또는 제한 사유 |
| `why_card` | object | UI/DB | 정량·정성·Peer·포트폴리오 핵심 근거 |
| `risk_card` | object | UI/DB | 악재, 데이터 결손, 모델 한계, 변동성 |
| `hard_rule_applied` | array | UI/DB | HOLD 강제, BUY 금지, 매수 비추천 등 적용 규칙 |
| `source_report_refs` | object | State/DB | `QuantReport`, `QualReport`, `CompetitorReport` 참조 ID |
| `disclaimer` | string | UI | 교육용 참고 정보 및 투자권유 아님 고지 |
| `cache_status` | enum | UI/DB | `cache_hit`, `cache_miss`, `refreshed` |
| `ActionRecommendation` | object | LangGraph State/DB | A6 PB 리포트에서 재사용할 최종 판단 결과 |

### 4.6 예외 처리

| 예외 상황 | 감지 조건 | 처리 방안 | 사용자 표시 |
|-----------|-----------|-----------|-------------|
| 종목 없음 | `company` 조회 결과 0건 | 분석 중단, B3 검색으로 복귀 유도 | `지원하지 않는 종목입니다.` |
| 선행 보고서 부족 | A1/A2/A3 중 2개 미만 확보 | BUY 금지, HOLD 또는 판단 보류 | `근거가 부족해 보수적으로 판단했습니다.` |
| 정량 핵심값 없음 | 현재가, 적정가, 안전마진 모두 없음 | BUY/SELL 결론 금지, 정성 참고만 제공 | `가격 근거가 부족해 행동 권유를 제한했습니다.` |
| 포트폴리오 없음 | `user_id` 없음 또는 `holdings` 미등록 | 일반 판단으로 진행, 적합도 제한 | `포트폴리오 정보가 없어 일반 기준으로 표시합니다.` |
| 현금 비중 없음 | `cash_ratio` null | 권유 비중 미표시, 방향만 제공 | `현금 비중이 없어 매수 비중은 제안하지 않습니다.` |
| BUY 신뢰도 60% 미만 | 1차 BUY && confidence < 60 | HOLD 강제 다운그레이드 | `신뢰도가 낮아 HOLD로 조정했습니다.` |
| BUY 포트 적합도 1점 | 1차 BUY && fit_score = 1 | HOLD 강제 다운그레이드 | `내 포트폴리오에는 적합도가 낮아 HOLD로 조정했습니다.` |
| 모든 시나리오 손실 예상 | A1 시나리오 전부 음의 안전마진 | 매수 비추천 또는 SELL 후보 표시 | `모든 시나리오에서 손실 가능성이 높습니다.` |
| 과도한 집중도 | 매수 후 단일 종목 비중이 정책 한도 초과 | BUY 금지 또는 비중 축소 제안 | `집중도 위험으로 추가 매수를 제한했습니다.` |
| 정성 리스크 심각 | A2에서 소송/규제/상장폐지 등 고위험 플래그 | 신뢰도 하향, HOLD/SELL 보수화 | `중대한 정성 리스크가 확인되었습니다.` |
| Peer 데이터 부족 | A3 Peer 3개 미만 또는 핵심 지표 결손 | Peer 근거 가중치 축소 | `동종업계 비교 근거가 제한적입니다.` |
| LLM 비용 3만원 도달 | 당월 사용액 >= 30,000원 | 설명 길이와 자체 검증 축소 | `비용 절감 모드로 요약이 간결하게 제공됩니다.` |
| LLM 비용 4만원 도달 | 당월 사용액 >= 40,000원 | LLM 호출 1회로 제한 | `비용 절감 정책에 따라 핵심 판단만 제공합니다.` |
| LLM 비용 5만원 도달 | 당월 사용액 >= 50,000원 | LLM 호출 중지, 규칙 기반 결론 제공 | `월 비용 상한 도달로 AI 종합 설명 생성을 중지했습니다.` |
| LLM 실패/타임아웃 | 호출 실패 또는 제한 시간 초과 | 규칙 기반 결론과 템플릿 근거로 대체 | `AI 종합 판단에 실패해 기본 판단을 표시합니다.` |
| Guardrail 차단 | 직접 주문 지시, 수익 보장, 금지 표현 감지 | 문구 수정 또는 결과 HOLD 보수화 | `일부 표현은 안전 정책에 따라 조정되었습니다.` |
| Pydantic 검증 실패 | `ActionRecommendation` 필수 필드 누락 | 저장 중단, HOLD 보수화 또는 재시도 | `권유 결과 검증에 실패했습니다.` |
| DB 저장 실패 | `analysis_history`/`analysis_cache` insert 실패 | UI 반환은 유지, 저장 실패 로깅 | `분석 결과 저장에 실패했습니다.` |

### 4.7 담당

| 영역 | 메인 담당 | 보조 담당 | 관련 테이블/모듈 | 설명 |
|------|-----------|-----------|------------------|------|
| 요청 라우팅 | Strategist | UI Controller | LangGraph State | B4/A1/A2/A3/B5에서 A4 실행 연결 |
| 선행 분석 수집 | Strategist | Quant/Qual/Competitor | `analysis_history`, LangGraph State | A1/A2/A3 결과 조회 또는 생성 |
| 포트폴리오 조회 | Strategist | Backend API | `users`, `holdings` | 보유 여부, 비중, 손익, 현금 비중 조회 |
| 점수 계산 | Strategist | Quant Worker | Python scoring module | 정량·정성·Peer·포트 적합도 점수 계산 |
| 결론 생성 | Strategist & Synthesizer | Guardrail | LLM Gateway, Prompt Store | BUY/HOLD/SELL 및 근거 문장화 |
| 하드 룰 적용 | Strategist | Guardrail | Rule Engine | 신뢰도/적합도/손실 시나리오 강제 조정 |
| 안전 검증 | Guardrail | Evaluator | 금지 표현 필터, RAGAS | 투자권유 오해, 수익 보장, PII 노출 차단 |
| 캐시 관리 | Strategist | Backend API | `analysis_cache`, `analysis_history` | 24시간 캐시 조회, 저장, 만료 관리 |
| 리포트 연계 | Report Worker | Strategist | `ActionRecommendation` | A6 PB 리포트의 결론 섹션 재사용 |
| 사용자 화면 | UI Controller | Strategist | Streamlit/Frontend | 한 줄 결론, 근거 카드, 책임 고지 렌더링 |

---

## 5. 기능-에이전트-DB-LLM 호출 매핑

| 단계 | 담당 에이전트 | DB/도구 | LLM 호출 | 비고 |
|------|---------------|---------|----------|------|
| 종목/세션 검증 | Strategist | `company`, `users` | 0회 | 코드와 권한 확인 |
| 캐시 조회 | Strategist | `analysis_cache`, `analysis_history` | 0회 | 24시간 내 동일 조건 결과 우선 |
| 선행 보고서 수집 | Strategist | LangGraph State, `analysis_history` | 0회 | A1/A2/A3 결과 재사용 |
| 포트폴리오 조회 | Strategist | `holdings` | 0회 | 보유 여부와 비중 |
| 1차 점수 계산 | Strategist | Python scoring module | 0회 | 수치 계산은 LLM 금지 |
| 결론 종합 | Strategist & Synthesizer | LLM Gateway | 최대 1회 | 비용 4만원 이상이면 이 호출만 유지 |
| 자체 검증 | Strategist | LLM Gateway | 최대 1회 | 비용 임계점 초과 시 생략 |
| Guardrail 검증 | Guardrail | LLM Gateway + 정규식 | 최대 1회 | 금지 표현/투자권유 오해 차단 |
| 이력 저장 | Strategist | `analysis_history`, `analysis_cache` | 0회 | A6 재사용 |

---

## 6. KPI / 비용 상한 / 운영 기준

| 지표 | 목표 | 측정 방식 |
|------|------|-----------|
| 단일 종목 종합 판단 시간 | 60초 이내 | 트리거부터 A4 결과 렌더링 완료까지 |
| 캐시 적중 응답 시간 | 5초 이내 | 24시간 캐시 존재 시 UI 표시 완료까지 |
| LLM 호출 수 | A4 실행당 최대 3회 | LLM Gateway 호출 로그 |
| 월 LLM 비용 | 50,000원 이하 | 운영 비용 집계 |
| Guardrail 차단 정확도 | 100% | 골든셋 시나리오 테스트 |
| BUY 하드 룰 위반 | 0건 | `hard_rule_applied`와 최종 결론 검증 |
| 책임 고지 표시율 | 100% | UI 렌더링 검증 |
| 선행 근거 참조율 | 100% | A1/A2/A3 또는 제한 판단 사유 포함 여부 |
| 스키마 검증 성공률 | 99% 이상 | `ActionRecommendation` 검증 로그 |

---

## 7. 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|-----------|
| 2026-05-23 | v1.0 | A4. BUY/HOLD/SELL 권유 기능별 상세 명세서 초안 작성 |


---

## 구현 상태 (코드 기준, 2026-06-14)

> 강사 #4(코드 우선) 정합 원칙 적용. 상충 시 **실제 코드가 우선**이며, 본 명세 §처리 흐름은 일부 목표 설계를 포함할 수 있다.
> 전체 기능 정합 매트릭스(SSOT): [`IMPLEMENTATION_STATUS.md`](../IMPLEMENTATION_STATUS.md)

- **상태**: 🟡 부분 구현
- **근거 / 미구현**: Strategist 신호 생성 + Guardrail 게이팅(#50) 동작. 전 케이스 HOLD 변별력은 과제.
- ⚠ 본 행은 코드 기준 PM 추정입니다. 해당 기능 담당의 확인이 필요합니다(`담당확인`).
