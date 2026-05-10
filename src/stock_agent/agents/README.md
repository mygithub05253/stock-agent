# `src/stock_agent/agents/` — 6 에이전트 구현

본 폴더는 시스템의 **6개 AI 에이전트** 구현을 담습니다. 각 에이전트는 LangGraph 노드로 등록되어 `src/stock_agent/graph/pipeline.py` 에서 오케스트레이션됩니다.

## 파일 매핑

| 파일 | 에이전트 | 한 줄 역할 | 강의 연계 |
|------|----------|-----------|-----------|
| `curator.py` | Curator Agent | 사용자 자연어 → 의도·종목·성향 파싱, 종목 미지정 시 후보 큐레이션 | W3 (ReAct) |
| `qual_worker.py` ⭐ | Qual Worker Agent | 뉴스·공시 RAG + 호재/악재 센티먼트 분석 | **W1 + W3** (핵심) |
| `quant_worker.py` | Quant Worker Agent | DART 재무 + pykrx 시세 → PER/PBR/성장률 계산, 5y 밸류에이션 | W3 (Tool) |
| `competitor.py` | Competitor Agent | 동종업계 Peer 추출 + 횡비교 Heatmap | W1 (Hybrid Search) |
| `strategist.py` | Strategist & Synthesizer Agent | 4 워커 결과 종합 → 매수/매도/홀드 + PB 리포트 작성 | W3 (ReAct) |
| `guardrail.py` | Guardrail & Evaluator Agent | PII/욕설/투자권유 필터 + RAGAS 자동 채점 | **W2 + W5** |

⭐ = 부트캠프 학습 핵심 적용 에이전트

## 작업 규칙

- **프롬프트는 코드에 섞지 않고** `src/stock_agent/prompts/` 에 별도 파일로 관리합니다. 비개발자(PM·기획)가 프롬프트만 수정할 수 있어야 합니다.
- 각 에이전트는 **Pydantic 스키마**(`src/stock_agent/schemas/`)에 정의된 입출력만 사용합니다. JSON 자유 형식 금지.
- LLM 호출은 **반드시** `src/stock_agent/llm/factory.py` 의 추상 함수를 통해 합니다. 모델 라우팅과 비용 추적이 한 곳에 모이도록.
- 에이전트 단위 테스트는 `tests/agents/test_<agent_name>.py` 에 작성합니다.

## 작업 충돌 방지

- 에이전트 1개 = 담당 1명 원칙. 같은 파일 동시 작업 금지.
- 공통 인터페이스(`AgentState` 스키마, `BaseAgent` 추상 클래스)가 변경되면 PR 시 전체 팀 알림 필수.
