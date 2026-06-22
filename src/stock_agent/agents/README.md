# `src/stock_agent/agents/` — 에이전트 구현

> 분류, 전문 분석, 합성, 안전 검증, 결과 렌더링을 각각 한 책임으로 구현한 실행 단위 모음입니다.

## 폴더 소개

- **What:** `run_*` 함수가 Pydantic `AgentState`를 받아 자신의 결과 필드만 갱신합니다.
- **Why:** 데이터 조회·LLM·오케스트레이션과 판단 책임을 분리해 독립 테스트와 폴백을 가능하게 합니다.
- Quant, Qual, Competitor, Macro는 LangGraph `Send`로 실제 병렬 실행됩니다.
- DB·RAG·LLM 경로와 결정적 fallback이 함께 구현되어 있습니다.
- ResultRenderer는 Tier 1/2/3와 다운로드 산출물용 데이터를 만듭니다.

## 기술 스택과 동작 원리

Python, Pydantic 2, PostgreSQL Tool, pgvector RAG, OpenRouter/GLM client를 사용합니다. 각 Agent는 [`graph/pipeline.py`](../graph/pipeline.py)가 노드로 감싸며 다른 Agent를 직접 호출하지 않습니다.

## 파일 매핑

| 파일 | 에이전트 | 한 줄 역할 | 강의 연계 |
|------|----------|-----------|-----------|
| `investor_profile.py` | Investor Profile Agent | 온보딩 답변을 투자성향, 투자기간, 손실감내, 유동성 니즈로 구조화 | W3 (Routing) |
| `curator.py` | Curator Agent | 사용자 자연어와 포트폴리오를 보고 분석 대상 종목/후보 큐레이션 | W3 (ReAct) |
| `request_classifier.py` | Request Classifier Agent | 질문을 intent, analysis_scope, urgency_reason으로 구조화 | W3 (Routing) |
| `investment_analyst.py` | Investment Analyst Agent | GLM으로 투자성향·포트폴리오·분석 근거를 종합해 최종 신호 보정 | W3 (Reasoning) |
| `qual.py` ⭐ | Qual Worker Agent | 뉴스·공시 RAG + 호재/악재 센티먼트 분석 | **W1 + W3** (핵심) |
| `quant.py` | Quant Worker Agent | DART 재무 + pykrx 시세 → PER/PBR/성장률 계산, 5y 밸류에이션 | W3 (Tool) |
| `competitor.py` | Competitor Agent | 동종업계 Peer 추출 + 횡비교 Heatmap | W1 (Hybrid Search) |
| `macro.py` | Macro Agent | 거시경제 지표(금리/환율/물가/성장) 기반 투자 환경 평가 | W3 (Tool) |
| `strategist.py` | Strategist & Synthesizer Agent | 정량·정성·Peer 결과 종합 → BUY/HOLD/SELL 성격의 분석 신호 + PB 리포트 작성 | W3 (ReAct) |
| `guardrail.py` | Guardrail & Evaluator Agent | PII/욕설/투자권유 필터 + RAGAS 자동 채점 | **W2 + W5** |
| `result_renderer.py` | Result Renderer | Tier 구조와 다운로드 산출물 생성 | UI |
| `recomposer.py` | Recomposer | Guardrail 수정 요구 시 제한 재합성 | 안전 |
| `fallback.py` | 공통 fallback 판별 | 예상 가능한 외부 장애만 폴백 | 안정성 |

⭐ = 부트캠프 학습 핵심 적용 에이전트

## Agent 책임 경계

| 에이전트 | 해야 하는 일 | 하지 않는 일 |
|----------|--------------|--------------|
| Investor Profile | 사용자 답변을 `UserProfile`로 구조화 | 종목 분석, 매수/매도 판단 |
| Curator | 분석 대상 종목과 후보 확정 | 질문 intent 분류, 정량 계산, 최종 투자 판단 |
| Request Classifier | 질문 intent, scope, urgency 분류 | 종목 lookup, 정량 계산, 최종 투자 판단 |
| Investment Analyst | GLM으로 최종 분석 신호와 포트폴리오 적합도 보정 | 근거 없는 숫자/뉴스 생성, 확정 투자권유 |
| Quant | 재무·시세 계산과 정량 해석 | LLM으로 숫자 생성 |
| Qual | RAG 검색 결과 기반 정성 분석 | 출처 없는 뉴스 요약 |
| Competitor | 같은 섹터 peer 선정과 비교 | 임의 peer 생성, 글로벌 peer 확장 |
| Macro | 거시경제 지표(금리/환율/물가/성장) 분석, 업종별 점수 산출, 거시 리스크 경고 | LLM으로 숫자 생성, 개별 종목 재무 분석 |
| Strategist | 사용자 포트폴리오 맥락에서 종합 | DB/API 직접 호출 남발 |
| Guardrail | 금융 표현, 근거 부족, PII, 평가 검증 | 새로운 투자 논리 생성 |

## 사용자 성향 반영 기준

사용자 성향은 모든 agent에 같은 강도로 반영하지 않습니다. 중간 전문 agent는 객관 근거를 만들고, 개인화는 주로 Curator와 Strategist에서 수행합니다.

| 에이전트 | 사용자 성향 반영 | 기준 |
|----------|------------------|------|
| Investor Profile | 매우 높음 | 온보딩 답변을 기반으로 성향 자체를 산출 |
| Curator | 높음 | 관심 섹터와 보유 종목을 보고 분석 대상/후보를 정함 |
| Request Classifier | 중간 | 질문 표현과 Curator 결과를 보고 route를 정함 |
| Quant | 낮음 | 수치 계산은 공통. 변동성 warning 정도만 다르게 표현 가능 |
| Qual | 낮음~중간 | 뉴스/공시 사실은 공통. 보수형에게 리스크를 더 명확히 표시 가능 |
| Competitor | 낮음 | Peer 비교는 공통 기준으로 수행 |
| Strategist | 매우 높음 | signal, suitability, 현금 비중, 추가매수/관망/비중축소 판단에 반영 |
| Guardrail | 동일 기준 | 모든 사용자에게 같은 금융 안전 기준 적용 |

따라서 같은 종목의 재무 수치, 뉴스 사실, peer 비교는 사용자마다 바뀌면 안 됩니다. 달라지는 것은 최종 포트폴리오 해석과 행동 신호입니다.

## 작업 규칙

- **프롬프트는 코드에 섞지 않고** `src/stock_agent/prompts/` 에 별도 파일로 관리합니다. 비개발자(PM·기획)가 프롬프트만 수정할 수 있어야 합니다.
- 각 에이전트는 **Pydantic 스키마**(`src/stock_agent/schemas/`)에 정의된 입출력만 사용합니다. JSON 자유 형식 금지.
- LLM 호출은 `src/stock_agent/llm/`의 GLM·OpenRouter 클라이언트를 통해 수행하고, Agent에서 API 키·HTTP 세부사항을 직접 다루지 않습니다.
- DB 조회, API 호출, 계산식은 `agents/`에 직접 넣지 않고 `src/stock_agent/tools/` 또는 `src/stock_agent/rag/` 로 분리합니다.
- 모든 agent output에는 가능한 한 `source`, `as_of_date`, `data_version`, `warnings`를 포함할 수 있도록 schema 확장을 고려합니다.
- 에이전트 단위 테스트는 `tests/agents/test_<agent_name>.py` 에 작성합니다.

## 에러핸들링 & 폴백 기준

- 외부 의존성(DB, API, RAG/embedding, LLM gateway) 실패는 에이전트가 가능한 한 fallback 결과를 만들어 파이프라인을 유지합니다.
- DB 연결은 테스트와 데모 경로가 오래 멈추지 않도록 짧은 `connect_timeout`과 단기 실패 캐시를 둡니다.
- 예상 가능한 외부 실패 판정은 `fallback.py`의 `should_fallback()`을 사용합니다. 코드 버그처럼 예상하지 못한 예외는 숨기지 않고 다시 raise합니다.
- fallback 결과에는 `fallback_reason` 또는 warning을 남겨 Strategist/Guardrail/UI가 신뢰도를 낮춰 표시할 수 있게 합니다.
- 민감정보가 들어간 `.env.example` 충돌은 항상 placeholder 값을 채택합니다. 실제 키와 DB URL은 `.env` 또는 배포 환경변수로만 관리합니다.
- 현재 구현 상태:
  - Quant: DB 연결 실패 시 보수적인 mock 지표와 risk를 반환합니다.
  - Qual: 뉴스/공시 RAG 검색 각각 실패 시 독립 fallback 문서를 반환합니다.
  - Competitor: peer DB 연결 실패 시 ① 자체 MCP 서버(stdio)로 pykrx 실시간 시세 기반 peer 비교(실데이터)를 시도하고, 그마저 불가하면 ② mock peer 비교와 warning을 반환합니다.
  - Macro: macro DB/tool 실패 시 mock 거시 지표와 risk를 반환합니다.
  - Guardrail: fallback 근거가 포함된 결과를 사용자 경고로 승격합니다.

## 작업 충돌 방지

- 에이전트 1개 = 담당 1명 원칙. 같은 파일 동시 작업 금지.
- 공통 인터페이스(`AgentState` 스키마, `BaseAgent` 추상 클래스)가 변경되면 PR 시 전체 팀 알림 필수.

## 주요 결과와 다음 개선

- 현재 UI는 핵심 진행 Agent 9개의 이벤트와 결과를 표시합니다.
- Quant, Qual, Competitor, Macro는 실제 데이터 우선·fallback 허용 방식으로 실행됩니다.
- 다음 개선은 RAG faithfulness 0.4096을 목표 0.80까지 높이는 근거 품질과 Input/Tool/Output Guardrail 세분화입니다.

```bash
python -m pytest tests/agents -v
python -m pytest tests/test_phase1_pipeline.py tests/test_result_renderer.py
```
