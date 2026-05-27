# User Intake / Curator Agent Handoff

| 항목 | 내용 |
|------|------|
| 작성일 | 2026-05-27 |
| 담당 범위 | 유저 데이터 수집, 유저 질문 정규화, 포트폴리오 초입, Curator output |
| 관련 코드 | `src/stock_agent/schemas/analysis.py`, `src/stock_agent/agents/curator.py`, `src/stock_agent/graph/pipeline.py` |
| 실행 예시 | `scripts/run_user_intake_demo.py` |
| 현재 상태 | Phase 1 mock pipeline 기준 |

---

## 1. 역할 요약

User Intake / Curator 단계는 사용자 입력을 다음 agent들이 처리하기 쉬운 구조화된 분석 요청으로 바꾸는 초입 단계다.

이 단계에서 해야 하는 일:

1. 사용자 투자성향을 `UserProfile`로 정규화한다.
2. 보유 종목 입력을 `Portfolio`와 `Holding`으로 정규화한다.
3. 자연어 질문을 `UserRequest`로 보존하고, Curator가 intent/target/scope를 채운다.
4. 분석 대상 종목을 확정하거나 candidates를 다음 단계에 넘긴다.
5. MVP 지원 범위 밖이면 warnings에 남긴다.
6. 질문을 category/urgency 기준으로 분기할 수 있게 `UserRequest`를 채운다.

하지 않는 일:

- PER, PBR, 수익률 같은 정량 계산을 LLM으로 만들지 않는다.
- BUY/HOLD/SELL 최종 판단을 Curator에서 내리지 않는다.
- 사용자에게 투자 권유성 문장을 생성하지 않는다.
- DB schema를 이 단계에서 임의로 확정하지 않는다.

---

## 2. Input Contract

### 2.1 `UserProfile`

사용자 성향과 제약 조건이다. Curator는 관심 섹터와 보유 종목 후보 선정에 사용하고, Strategist는 최종 suitability 계산에 강하게 사용한다.

| 필드 | 예시 | 사용처 |
|------|------|--------|
| `user_id` | `demo-park` | 분석 이력, 세션 식별 |
| `risk_tolerance` | `low`, `medium`, `high` | Strategist 개인화 |
| `investment_horizon_months` | `12` | Strategist 개인화 |
| `target_return_rate` | `0.1` | 목표수익률 context |
| `max_drawdown_tolerance` | `-0.1` | 손실감내도 context |
| `investment_goal` | `growth` | UI/Strategist context |
| `experience_level` | `beginner` | 설명 난이도 조정 후보 |
| `cash_source` | `surplus_cash` | 자금 성격 |
| `preferred_sectors` | `["반도체", "금융"]` | Curator 후보 추천 |
| `excluded_sectors` | `["바이오"]` | 후보 제외 후보 |
| `liquidity_need_level` | `high` | Strategist 적합도 |

### 2.2 `Portfolio` / `Holding`

사용자 보유 종목 원장과 시스템 계산값을 분리한다.

| 필드 | 예시 | 입력 주체 | 설명 |
|------|------|-----------|------|
| `stock_code` | `005930` | 사용자/검색 | KRX 6자리 코드 |
| `corp_name` | `삼성전자` | 검색/DB | 종목명 |
| `sector` | `반도체` | DB/현재 mock | MVP 지원 산업 |
| `avg_price` | `72000` | 사용자 | 평균 매수가 |
| `qty` | `10` | 사용자 | 보유 수량 |
| `bought_at` | `2026-05-01` | 사용자 | 대표 매수일 |
| `current_price` | `78000` | 시스템 | 현재 mock에서는 고정값 |
| `weight` | `0.32` | 시스템 계산 | 포트폴리오 평가금액 기준 비중 |

계산 helper:

| 속성/함수 | 설명 |
|-----------|------|
| `Holding.cost_basis` | `avg_price * qty` |
| `Holding.market_value` | `current_price * qty` |
| `Portfolio.total_market_value` | 모든 holding의 `market_value` 합 |
| `Portfolio.sector_weights()` | 섹터별 평가금액 비중 |

### 2.3 `UserRequest`

사용자 자연어 질문을 보존하고, Curator가 구조화 정보를 채운다.

| 필드 | Curator 전 | Curator 후 예시 |
|------|------------|-----------------|
| `raw_query` | `삼성전자 급등했는데 안정형이면 어떻게 할까?` | 동일 |
| `intent` | `None` | `holding_review` |
| `target_stock_code` | `None` | `005930` |
| `target_corp_name` | `None` | `삼성전자` |
| `analysis_scope` | `None` | `single_stock` |
| `urgency_reason` | `None` | `surge`, `drop`, `earnings`, `news`, `general` |
| `requested_depth` | `summary` | `summary` |

---

## 3. Conversation Intake Plan

초기 제품에서는 사용자가 한 번에 모든 정보를 입력하지 않을 수 있다. 따라서 초입 agent는 대화형으로 부족한 정보를 채우고, 충분해진 뒤 DB에 저장하는 방향이 맞다.

### 3.1 큰 계획

카드형 대화 수집 UI는 “사용자에게 질문을 여러 개 던지고, 답변을 구조화해서 메모리에 쌓은 뒤, 포트폴리오 분석으로 연결하는 초입 agent 화면”이다.

```text
카드형 질문
-> 답변 수집
-> 답변 유형 분류
-> session_state 저장
-> 보유 종목 수집
-> 포트폴리오 요약 생성
-> 사용자 질문 수신
-> intent/category/urgency 분기
-> 기존 multi-agent pipeline 실행
```

큰 목표는 다음 5개다.

| 목표 | 설명 |
|------|------|
| 카드형 수집 UX | 뉴스 카드처럼 하나씩 읽히는 질문 카드로 유저 정보를 받는다. |
| 메모리 우선 저장 | DB 확정 전까지 `st.session_state`에 `profile`, `portfolio`, `messages`를 저장한다. |
| 보유 종목 자연어 입력 | `삼성전자 10주, SK하이닉스 3주` 같은 입력을 구조화한다. |
| 질문 분기 | 이후 질문을 `intent`, `analysis_scope`, `urgency_reason`으로 나눈다. |
| 다음 agent handoff | `UserProfile`, `Portfolio`, `UserRequest`, `CuratorResult`를 기존 pipeline에 넘긴다. |

### 3.2 세부 계획

#### Step 1. Session State 구조

Streamlit 메모리는 다음 key를 사용한다.

| key | 타입 | 설명 |
|-----|------|------|
| `intake_profile` | dict | 카드 질문으로 수집한 투자성향 |
| `intake_portfolio` | dict/list | 보유 종목 입력 결과 |
| `intake_messages` | list[dict] | 유저와 시스템 간 대화/카드 기록 |
| `intake_stage` | string | 현재 단계: `profile`, `portfolio`, `ready`, `analysis` |
| `analysis_output` | AnalysisOutput | 기존 pipeline 결과 |

#### Step 2. 카드형 질문 구성

1차 MVP 질문 카드는 다음 순서로 둔다.

| 순서 | 카드 질문 | 저장 필드 |
|------|-----------|-----------|
| 1 | 투자성향은 안정형/중립형/공격형 중 어디에 가까운가요? | `risk_tolerance` |
| 2 | 투자 기간은 어느 정도인가요? | `investment_horizon_months` |
| 3 | 감내 가능한 손실 폭은 어느 정도인가요? | `max_drawdown_tolerance` |
| 4 | 관심 산업은 반도체/금융 중 어디인가요? | `preferred_sectors` |
| 5 | 보유 종목을 알려주세요. 예: 삼성전자 10주, SK하이닉스 3주 | `holdings` |
| 6 | 이제 궁금한 점을 질문해 주세요. | `raw_query` |

#### Step 3. 보유 종목 자연어 파싱

1차 MVP에서는 정규식 기반으로 처리한다.

입력 예시:

```text
삼성전자 10주, SK하이닉스 3주
```

출력 예시:

```json
[
  {"corp_name": "삼성전자", "stock_code": "005930", "qty": 10, "sector": "반도체"},
  {"corp_name": "SK하이닉스", "stock_code": "000660", "qty": 3, "sector": "반도체"}
]
```

제한:

- 평균 매수가는 사용자가 주지 않으면 mock 현재가를 기본값으로 둔다.
- 종목 master는 현재 `_STOCK_OPTIONS` 또는 Curator alias와 맞춘다.
- 파싱 실패한 항목은 warning으로 보여준다.

#### Step 4. 포트폴리오 요약 카드

보유 종목을 파싱하면 바로 다음 값을 보여준다.

| 항목 | 계산 |
|------|------|
| 총 평가금액 | `sum(current_price * qty)` |
| 종목별 비중 | `holding.market_value / total_market_value` |
| 섹터 비중 | `Portfolio.sector_weights()` |
| 현금 비중 | `cash_weight` |

#### Step 5. 질문 분기

유저 질문은 Curator에서 다음처럼 분기한다.

| 예시 질문 | intent | urgency |
|-----------|--------|---------|
| `삼성전자 계속 가져가도 돼?` | `holding_review` | `general` |
| `SK하이닉스 비중 괜찮아?` | `risk_review` | `general` |
| `삼성전자 급락했는데 손절해야 해?` | `sell_decision` | `drop` |
| `삼성전자 공시 이슈 확인해줘` | `holding_review` | `news` |
| `내 포트폴리오 전체 봐줘` | `portfolio_review` | `general` |

#### Step 6. DB 저장 전환 시점

1차 MVP는 session memory만 사용한다. DB 연결은 다음 조건이 충족된 뒤 진행한다.

| 조건 | 설명 |
|------|------|
| `users` schema 합의 | 프로필 저장 필드 확정 |
| `holdings` schema 합의 | 보유 종목 원장 저장 필드 확정 |
| 개인정보/민감정보 정책 합의 | 이메일, 이름, 투자성향 로그 처리 기준 |
| 저장 UX 합의 | 자동 저장인지, 저장 버튼인지 결정 |

### 3.3 1차 구현 범위

이번 1차 구현은 너무 크게 가지 않고 다음만 포함한다.

- [ ] 카드형 intake 화면을 Streamlit 메인 영역에 추가
- [ ] `st.session_state`에 profile/portfolio/messages 저장
- [ ] `삼성전자 10주, SK하이닉스 3주` 형태의 보유 종목 입력 파서 추가
- [ ] 포트폴리오 요약 카드 추가
- [ ] 질문 입력 시 기존 `run_phase1_analysis()` 연결
- [ ] 기존 sidebar 입력은 fallback/debug 용도로 유지 또는 축소

이번 1차 구현에서 제외한다.

- [ ] 실제 DB 저장
- [ ] 실제 GLM/LLM 호출
- [ ] 실시간 가격 조회
- [ ] 완전한 자유 채팅 파서
- [ ] 포트폴리오 전체 종목별 loop 분석

---

권장 흐름:

```text
사용자 첫 진입
-> 투자성향/목표/손실감내도 질문
-> 보유 종목/평단/수량/현금비중 질문
-> UserProfile + Portfolio 완성도 확인
-> 충분하면 users/holdings 저장
-> 이후 질문은 UserRequest로 정규화
-> intent/category에 따라 분석 route 분기
```

MVP에서는 DB 저장 전까지 Streamlit session/mock 객체로 유지하고, DB schema 합의 후 다음 순서로 저장한다.

| 단계 | 저장 대상 | 설명 |
|------|-----------|------|
| 프로필 수집 완료 | `users` | 투자성향, 목표수익률, 손실감내도, 관심 산업 |
| 포트폴리오 수집 완료 | `holdings` | 종목코드, 평균 매수가, 수량, 대표 매수일 |
| 분석 실행 완료 | `analysis_history` | request/profile/portfolio snapshot과 최종 output |

필수 수집값:

| 구분 | 최소 필요값 |
|------|-------------|
| 투자성향 | `risk_tolerance`, `investment_horizon_months`, `max_drawdown_tolerance`, `preferred_sectors` |
| 포트폴리오 | `stock_code`, `avg_price`, `qty`, `cash_weight` |
| 질문 | `raw_query` |

부족한 값이 있으면 분석을 바로 실행하지 않고 보강 질문을 먼저 한다. 예를 들어 보유 종목이 없으면 “보유 종목을 먼저 알려주세요”, 관심 산업이 비어 있으면 “반도체/금융 중 관심 산업을 선택해 주세요”처럼 처리한다.

---

## 4. Question Routing

Curator는 질문을 다음 기준으로 분기한다.

| 분기 필드 | 값 | 감지 기준 | 후속 처리 |
|-----------|----|-----------|-----------|
| `intent` | `holding_review` | 보유 종목 일반 점검 | 단일 종목 분석 |
| `intent` | `risk_review` | `위험`, `리스크`, `괜찮`, `비중`, `손실` | 리스크/비중 중심 표시 |
| `intent` | `sell_decision` | `팔`, `매도`, `익절`, `손절`, `정리` | 매도 판단 보조 |
| `intent` | `portfolio_review` | 종목 미지정 포트폴리오 질문 | 후보 또는 bulk 분석 |
| `intent` | `new_recommendation` | 보유 외 관심 종목 | 신규 관심 종목 점검 |
| `urgency_reason` | `surge` | `급등`, `상승`, `올랐` | 추격 매수 주의/리밸런싱 |
| `urgency_reason` | `drop` | `급락`, `하락`, `떨어졌`, `빠졌` | 손실 허용 범위 확인 |
| `urgency_reason` | `earnings` | `실적`, `어닝`, `발표` | 실적 이벤트 중심 |
| `urgency_reason` | `news` | `뉴스`, `공시`, `이슈` | Qual/RAG 중심 |
| `urgency_reason` | `general` | 위 조건 없음 | 일반 분석 |

현재 Phase 1은 모든 route가 같은 mock pipeline을 탄다. 후속 구현에서는 `intent`와 `urgency_reason`에 따라 UI 강조 영역과 agent 호출 깊이를 바꾼다.

---

## 5. Curator Output Contract

Curator의 output은 `AgentState.curator`에 저장되는 `CuratorResult`다.

| 필드 | 예시 | 다음 단계 사용처 |
|------|------|------------------|
| `intent` | `보유 종목 판단 지원` | UI 표시, routing |
| `corp_name` | `삼성전자` | Quant/Qual/Competitor 표시 |
| `stock_code` | `005930` | price/holding lookup |
| `corp_code` | `00126380` | DART 재무/공시 lookup |
| `sector` | `반도체` | Peer/산업 제한 |
| `candidates` | `["삼성전자", "SK하이닉스"]` | 종목 미지정 시 후보 표시 |
| `warnings` | `["MVP 지원 산업은 반도체/금융 중심입니다: ..."]` | UI/Guardrail 표시 |

현재 Curator 동작:

| 질문 유형 | 처리 |
|-----------|------|
| 질문에 종목명/종목코드 있음 | alias 또는 보유 종목에서 target 확정 |
| 질문에 종목 없음 | 선호 섹터와 보유 종목 기반 candidates 생성 |
| 보유 종목도 없음 | MVP 기본 후보 반환 |
| 지원 산업 밖 | warning 생성 |

---

## 6. Handoff To Next Agents

다음 agent는 User Intake output을 이렇게 사용한다.

| 다음 단계 | 사용하는 값 | 사용 방식 |
|-----------|-------------|-----------|
| Quant | `curator.stock_code`, `curator.corp_code` | 재무/가격 조회 키 |
| Qual | `curator.stock_code`, `curator.corp_code`, `user_request.raw_query` | 뉴스/공시 RAG 검색 키 |
| Competitor | `curator.sector`, `curator.stock_code` | Peer 후보 선정 |
| Strategist | `user_profile`, `portfolio`, `curator`, worker 결과 | suitability와 next action 개인화 |
| Guardrail | 최종 문장, warnings | 투자권유성 표현 완화 |

중요한 경계:

- Quant/Qual/Competitor는 사용자 성향을 강하게 반영하지 않는다.
- Strategist가 사용자 성향, 보유 비중, 현금 필요도, 투자 기간을 강하게 반영한다.
- Guardrail은 모든 사용자에게 동일한 금융 안전 기준을 적용한다.

---

## 7. Example Outputs

### 5.1 보유 종목 직접 질문

입력:

```text
내 포트폴리오에서 삼성전자 어떻게 할까?
```

예상 Curator output:

```json
{
  "intent": "보유 종목 판단 지원",
  "corp_name": "삼성전자",
  "stock_code": "005930",
  "corp_code": "00126380",
  "sector": "반도체",
  "candidates": [],
  "warnings": []
}
```

예상 `UserRequest`:

```json
{
  "raw_query": "내 포트폴리오에서 삼성전자 어떻게 할까?",
  "intent": "holding_review",
  "target_stock_code": "005930",
  "target_corp_name": "삼성전자",
  "analysis_scope": "single_stock",
  "urgency_reason": "general",
  "requested_depth": "summary"
}
```

### 5.2 종목 미지정 포트폴리오 질문

입력:

```text
요즘 내 포트폴리오에서 볼만한 종목 알려줘
```

예상 Curator output:

```json
{
  "intent": "포트폴리오 전체 점검",
  "corp_name": "삼성전자",
  "stock_code": "005930",
  "corp_code": null,
  "sector": "반도체",
  "candidates": ["삼성전자", "SK하이닉스"],
  "warnings": []
}
```

주의:

- 현재 Phase 1에서는 대표 후보 1개를 target으로 잡아 기존 단일 종목 pipeline에 태운다.
- 진짜 포트폴리오 전체 분석은 후속 `BulkPortfolioAdvice` 또는 종목별 loop로 분리해야 한다.

### 5.3 안정형 + 고비중 + 급등 질문

입력:

```text
삼성전자 급등했는데 안정형이면 어떻게 할까?
```

예상 Strategist output 특징:

```json
{
  "signal": "HOLD",
  "confidence": 69,
  "suitability": 34,
  "next_actions": [
    "안정형 성향 대비 보유 비중이 높아 비중 확대보다 리밸런싱 기준을 먼저 정합니다.",
    "급등 이후에는 추격 매수보다 목표 비중과 이익 실현 기준을 먼저 확인합니다."
  ]
}
```

핵심은 `signal`과 `suitability`를 분리하는 것이다. 종목 자체 신호가 나쁘지 않아도, 안정형 사용자에게 이미 비중이 높으면 적합도는 낮아질 수 있다.

---

## 8. Local Demo

터미널에서 다음 명령으로 초입 agent output을 확인할 수 있다.

```bash
PYTHONPATH=src python3 scripts/run_user_intake_demo.py
```

가상환경을 사용하는 경우:

```bash
.venv/bin/python scripts/run_user_intake_demo.py
```

특정 질문만 확인:

```bash
.venv/bin/python scripts/run_user_intake_demo.py --query "SK하이닉스 비중 괜찮아?"
```

안정형 고비중 시나리오:

```bash
.venv/bin/python scripts/run_user_intake_demo.py --scenario conservative_surge
```

출력은 다음 묶음을 포함한다.

| 출력 키 | 설명 |
|---------|------|
| `input` | 입력 질문, profile, portfolio 요약 |
| `user_request` | Curator가 채운 구조화 질문 |
| `curator` | 초반 에이전트 output |
| `tier1` | 최종 한 줄 결과 |
| `strategist_next_actions` | 사용자 맥락 기반 다음 행동 |

---

## 9. Known Gaps

| Gap | 설명 | 다음 작업 |
|-----|------|-----------|
| 실제 LLM/GLM 호출 없음 | 현재는 mock pipeline | `src/stock_agent/llm/` adapter 필요 |
| 종목 master 하드코딩 | Streamlit/Curator에 MVP 후보가 박혀 있음 | `company` DB lookup 연결 |
| 포트폴리오 전체 분석 미완성 | 종목 미지정 시 대표 후보 1개로 분석 | bulk pipeline 설계 |
| portfolio route 분리 미완성 | 현재는 대표 후보 1개로 단일 종목 pipeline 실행 | `BulkPortfolioAdvice` 또는 종목별 loop 설계 |
| DB 저장 없음 | UserProfile/Holding은 세션/mock 상태 | `users`, `holdings` schema 합의 후 연결 |

---

## 10. 변경 이력

| 날짜 | 변경 내용 |
|------|-----------|
| 2026-05-27 | User Intake / Curator output handoff 문서 작성 |
