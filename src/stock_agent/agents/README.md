# `src/stock_agent/agents/` — 6 에이전트 구현

본 폴더는 시스템의 **6개 AI 에이전트** 구현을 담습니다.

현재 Phase 1은 mock 함수 기반으로 동작하며, 목표 구조는 각 에이전트를 LangGraph 노드로 등록해 `src/stock_agent/graph/pipeline.py` 에서 오케스트레이션하는 것입니다. 자세한 아키텍처 기준은 `docs/architecture/multi_agent_architecture.md` 를 따릅니다.

## 파일 매핑

| 파일 | 에이전트 | 한 줄 역할 | 강의 연계 |
|------|----------|-----------|-----------|
| `curator.py` | Curator Agent | 사용자 자연어 → 의도·종목·성향 파싱, 종목 미지정 시 후보 큐레이션 | W3 (ReAct) |
| `qual.py` ⭐ | Qual Worker Agent | 뉴스·공시 RAG + 호재/악재 센티먼트 분석 | **W1 + W3** (핵심) |
| `quant.py` | Quant Worker Agent | DART 재무 + pykrx 시세 → PER/PBR/성장률 계산, 5y 밸류에이션 | W3 (Tool) |
| `competitor.py` | Competitor Agent | 동종업계 Peer 추출 + 횡비교 Heatmap | W1 (Hybrid Search) |
| `strategist.py` | Strategist & Synthesizer Agent | 정량·정성·Peer 결과 종합 → BUY/HOLD/SELL 성격의 분석 신호 + PB 리포트 작성 | W3 (ReAct) |
| `guardrail.py` | Guardrail & Evaluator Agent | PII/욕설/투자권유 필터 + RAGAS 자동 채점 | **W2 + W5** |

⭐ = 부트캠프 학습 핵심 적용 에이전트

## Agent 책임 경계

| 에이전트 | 해야 하는 일 | 하지 않는 일 |
|----------|--------------|--------------|
| Curator | 종목/의도/분석 타입 확정 | 정량 계산, 최종 투자 판단 |
| Quant | 재무·시세 계산과 정량 해석 | LLM으로 숫자 생성 |
| Qual | RAG 검색 결과 기반 정성 분석 | 출처 없는 뉴스 요약 |
| Competitor | 같은 섹터 peer 선정과 비교 | 임의 peer 생성, 글로벌 peer 확장 |
| Strategist | 사용자 포트폴리오 맥락에서 종합 | DB/API 직접 호출 남발 |
| Guardrail | 금융 표현, 근거 부족, PII, 평가 검증 | 새로운 투자 논리 생성 |

## 작업 규칙

- **프롬프트는 코드에 섞지 않고** `src/stock_agent/prompts/` 에 별도 파일로 관리합니다. 비개발자(PM·기획)가 프롬프트만 수정할 수 있어야 합니다.
- 각 에이전트는 **Pydantic 스키마**(`src/stock_agent/schemas/`)에 정의된 입출력만 사용합니다. JSON 자유 형식 금지.
- LLM 호출은 향후 **반드시** `src/stock_agent/llm/factory.py` 의 추상 함수를 통해 합니다. 모델 라우팅과 비용 추적이 한 곳에 모이도록.
- DB 조회, API 호출, 계산식은 `agents/`에 직접 넣지 않고 `src/stock_agent/tools/` 또는 `src/stock_agent/rag/` 로 분리합니다.
- 모든 agent output에는 가능한 한 `source`, `as_of_date`, `data_version`, `warnings`를 포함할 수 있도록 schema 확장을 고려합니다.
- 에이전트 단위 테스트는 `tests/agents/test_<agent_name>.py` 에 작성합니다.

## 작업 충돌 방지

- 에이전트 1개 = 담당 1명 원칙. 같은 파일 동시 작업 금지.
- 공통 인터페이스(`AgentState` 스키마, `BaseAgent` 추상 클래스)가 변경되면 PR 시 전체 팀 알림 필수.

## 구현 우선순위

1. Curator를 `company` DB 기반 종목 lookup으로 교체
2. Quant를 `stock_price`, `financial_statement` 기반 계산으로 교체
3. Qual에 `rag/pgvector_store.py` 검색 결과 연결
4. Competitor에 peer 선정 기준과 비교 지표 연결
5. Strategist에 포트폴리오 적합도와 self-critique 반영
6. Guardrail을 Input/Tool/Output 3계층으로 확장
