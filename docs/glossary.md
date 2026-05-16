# 용어집 (Glossary)

| 항목 | 값 |
|------|-----|
| 작성자 | PM |
| 작성일 | 2026-05-10 |
| 버전 | v0.1 |
| 대상 | 비전공자 팀원·다른 PM·강사 검토 시 참고 |

---

## 0. 이 문서를 쓰는 법

문서를 읽다가 모르는 용어가 있으면 먼저 여기서 찾으세요. 없으면 PM 단톡방에 질문하시고, PM이 여기 추가해드립니다.

---

## A. AI / 에이전트

| 용어 | 한 줄 설명 | 더 알아보기 |
|------|-----------|-------------|
| **AI Agent (에이전트)** | LLM에게 *도구* 와 *목표* 를 주고 스스로 판단·실행하게 하는 단위 | 우리 시스템엔 6명 (Curator·Qual·Quant·Competitor·Strategist·Guardrail) |
| **LLM** | Large Language Model. ChatGPT·Claude·Solar 같은 대화 모델 | OpenAI·Anthropic·Upstage |
| **Solar** | Upstage 사가 만든 한국어 특화 LLM. 부트캠프 무료 크레딧 제공 | https://www.upstage.ai/solar |
| **GPT-4o-mini** | OpenAI의 저렴 모델. 토큰당 0.0001달러 수준 | 단순 작업용 |
| **Claude Haiku** | Anthropic의 저렴·빠른 모델 | |
| **Multi-agent** | 에이전트 여러 개가 협업하는 구조 | 우리는 LangGraph로 묶음 |
| **LangGraph** | LangChain 사가 만든 멀티에이전트 오케스트레이션 라이브러리 | StateGraph + Conditional Edge + Send API |
| **ReAct** | Reasoning + Acting. *생각하고 → 행동하고 → 관찰하는* 루프로 작동하는 에이전트 패턴 | W3 학습 핵심 |
| **A2A** | Agent-to-Agent. 에이전트끼리 메시지로 협업하는 패턴 | 10주차 도입 |
| **Tool** | 에이전트가 사용할 수 있는 외부 함수 (검색·계산·API 호출) | LangChain `@tool` 데코레이터 |
| **Pydantic** | 파이썬에서 데이터 형식을 강제하는 라이브러리 | LLM 응답 파싱 안정성 ↑ |
| **MCP** | Model Context Protocol. LLM이 도구·데이터에 접근하는 표준 | (참고용) |

---

## B. RAG / 검색

| 용어 | 한 줄 설명 |
|------|-----------|
| **RAG** | Retrieval-Augmented Generation. "검색해서 그 결과를 바탕으로 답변" |
| **Embedding (임베딩)** | 텍스트를 숫자 벡터로 변환한 것. 벡터끼리 거리가 가까우면 의미가 비슷 |
| **Vector DB (벡터 DB)** | 임베딩을 저장하고 유사도 검색해주는 저장소. 우리는 Postgres + pgvector를 기본 사용 |
| **Chroma** | 가벼운 오픈소스 벡터 DB. 향후 optional RAG backend 후보 |
| **BM25** | 키워드 기반 검색 알고리즘. 전통적 검색 엔진의 기본 |
| **Hybrid Search** | BM25 + 벡터 검색을 같이 쓰는 방식. W1 학습 핵심 |
| **Reranker** | 검색 결과를 다시 정렬해서 상위 N개 품질을 높이는 모듈 |
| **BGE-m3** | 다국어 지원 임베딩 모델. 한국어 성능 좋음 |
| **Chunk (청크)** | 긴 문서를 작게 자른 단위. 보통 512 토큰 |

---

## C. 평가 / 가드레일

| 용어 | 한 줄 설명 |
|------|-----------|
| **RAGAS** | RAG 시스템 평가 라이브러리. faithfulness·context precision 등 자동 채점 |
| **Faithfulness** | LLM 답변이 *RAG로 검색한 컨텍스트에 충실한지* 점수 (0~1) |
| **Context Precision** | 검색 결과 중 답변에 *실제 사용된 비율* |
| **Action Consistency** | 같은 질문 N번 했을 때 답이 일관적인지 |
| **Self-Consistency** | LLM에 같은 질문 N번 시켜서 다수결로 결정 |
| **Guardrail** | LLM 출력을 *안전하게* 만드는 필터·검증 |
| **Trustworthiness** | 결과 발표 직전 가격 급변동 등 재확인 |
| **Hallucination (환각)** | LLM이 사실 아닌 것을 자신 있게 말하는 현상 |
| **PII** | Personally Identifiable Information. 이름·생년월일·계좌번호 등 |
| **Prompt** | LLM에게 주는 지시문 |
| **System Prompt** | 에이전트의 역할·규칙을 정의하는 긴 시스템 프롬프트 |
| **Few-shot** | 프롬프트에 예시 N개 첨부 |
| **Adversarial Critic** | "내 답을 공격해봐" 시키는 자체 검증 패턴 |

---

## D. 금융 / 투자

| 용어 | 한 줄 설명 |
|------|-----------|
| **DART** | 금융감독원 전자공시시스템. 한국 상장사 재무·공시 공식 데이터 |
| **OpenDART** | DART 의 무료 API |
| **pykrx** | KOSPI/KOSDAQ 시세를 가져오는 파이썬 라이브러리 |
| **FinanceDataReader (FDR)** | 시세·종목 마스터 가져오는 라이브러리 |
| **ECOS** | 한국은행 경제통계시스템. 기준금리·환율·CPI |
| **FRED** | 미국 연준의 매크로 통계 |
| **KOSPI** | 한국 대형주 시장 |
| **KOSDAQ** | 한국 중소형주 시장 |
| **OHLCV** | Open·High·Low·Close·Volume. 일봉 데이터 |
| **PER** | Price/Earnings. 주가 ÷ 주당순이익 |
| **PBR** | Price/Book. 주가 ÷ 주당순자산 |
| **EPS** | Earnings Per Share. 주당순이익 |
| **ROE** | Return on Equity. 자본 대비 순이익률 |
| **OPM** | Operating Profit Margin. 영업이익률 |
| **CAPEX** | Capital Expenditure. 설비투자 |
| **FCF** | Free Cash Flow. 잉여현금흐름 |
| **DCF** | Discounted Cash Flow. 미래 현금흐름 할인해서 적정가 산출 |
| **WACC** | Weighted Average Cost of Capital. 가중평균자본비용 (DCF 할인율) |
| **Terminal Value** | DCF에서 "5년 후 영원히" 가치 |
| **g (성장률)** | DCF 영구성장률 |
| **DDM** | Dividend Discount Model. 배당할인모형 |
| **상대가치** | Peer 회사들의 PER·PBR 평균으로 적정가 산출 |
| **MoS** | Margin of Safety. 안전마진 = (적정가 − 현재가) ÷ 적정가 |
| **PB** | Private Banker. 은행·증권 자산관리 전담 직원 |
| **Peer** | 같은 산업의 경쟁사. 비교 분석 대상 |
| **Sector** | 산업 분류 (반도체·금융·소비재 등) |
| **GIC** | Global Industry Classification. 글로벌 산업 분류 |
| **KSIC** | 한국 표준 산업 분류 |
| **알파 (α)** | 시장 대비 초과수익률 |
| **백테스트** | 과거 데이터로 추천을 적용했을 때 수익률 시뮬레이션 |

---

## E. PM / 프로세스

| 용어 | 한 줄 설명 |
|------|-----------|
| **PRD** | Product Requirements Document. 요구사항 정의서 |
| **Functional Spec** | 기능 명세서. 각 기능의 동작 상세 |
| **ADR** | Architecture Decision Record. 의사결정 기록 |
| **MVP** | Minimum Viable Product. 핵심 가치만 검증하는 최소 버전 |
| **User Story** | "As a [유저], I want to [행동], so that [이유]" 형식 |
| **Phase** | 구현 단계. 우리는 Phase 1 (MVP) → Phase 2 (고급) → Phase 3 (v2) |
| **Sprint** | 짧은 기간(보통 1~2주) 안에 완성해야 할 작업 묶음 |
| **Milestone** | 큰 기간 단위 목표 (중간 시연·최종 발표 등) |
| **Edge Case** | 흔하지 않지만 발생 시 시스템이 깨지는 예외 상황 |
| **Persona** | 가상의 대표 사용자. 우리는 박민호·김재현·이지영 |
| **In/Out of Scope** | 이번에 할 것 / 안 할 것 |
| **Non-goal** | 명시적으로 *하지 않는 것* |
| **Go/No-Go** | 다음 단계 진입 여부 결정 |
| **Backlog** | 나중에 할 작업 대기열 |
| **Stakeholder** | 이해관계자 — 강사·교수·팀원·심사위원 |

---

## F. 개발 / 인프라

| 용어 | 한 줄 설명 |
|------|-----------|
| **Streamlit** | 파이썬으로 웹 화면 만드는 프레임워크 |
| **Streamlit Cloud** | Streamlit 무료 배포 서비스 |
| **Postgres** | 오픈소스 관계형 DB |
| **pgvector** | Postgres 안에서 임베딩 벡터를 저장하고 유사도 검색하는 확장 |
| **Docker** | 애플리케이션을 컨테이너로 실행하는 도구 |
| **docker-compose** | 여러 컨테이너를 한 번에 띄우는 도구 |
| **Dockerfile** | Docker 이미지 빌드 정의 파일 |
| **.env** | 환경 변수 파일 (API 키 등). 절대 git 커밋 X |
| **pyproject.toml** | Python 의존성·설정 파일 |
| **virtualenv** | Python 가상 환경 (.venv) |
| **pytest** | Python 테스트 프레임워크 |
| **ruff** | Python 코드 린터 (자동 정리) |
| **CI** | Continuous Integration. PR마다 자동 테스트 |
| **LangSmith** | LLM·LangGraph 호출 트레이싱·디버깅 도구 |
| **REST API** | HTTP로 데이터 주고받는 표준 |

---

## G. Git / 협업

| 용어 | 한 줄 설명 |
|------|-----------|
| **Git** | 버전 관리 도구 |
| **GitHub** | Git 호스팅 서비스 |
| **Repo (레포)** | Repository. 프로젝트 저장소 |
| **Branch** | 작업 갈래. main / dev / feature/p2-xxx |
| **Commit** | 변경사항 저장 단위 |
| **Push** | 내 컴퓨터 → GitHub 업로드 |
| **Pull** | GitHub → 내 컴퓨터 다운로드 |
| **PR** | Pull Request. "내 작업을 메인에 합쳐달라" 요청 |
| **Merge** | 두 브랜치를 합치기 |
| **Conflict** | Merge 시 충돌. 같은 줄을 두 사람이 다르게 수정 |
| **.gitignore** | git이 무시할 파일·폴더 목록 |
| **PR 검수 (Review)** | 다른 사람이 PR 내용을 확인하고 승인/지적 |

---

## H. 자주 헷갈리는 약어

| 약어 | 풀이 | 자주 쓰는 곳 |
|------|------|--------------|
| **W1~W5** | Week 1 ~ Week 5 (부트캠프 주차) | 강의 매핑 |
| **P1~P5** | Person 1~5 (팀원 ID) | 브랜치명 |
| **BD** | Big Data | 부트캠프 명칭 (BDAI) |
| **BDAI** | Big Data + AI | 본 부트캠프 |
| **PoCaT** | 본 부트캠프 별칭 | (출처: 강사) |
| **MTS** | Mobile Trading System (모바일 증권 앱) | 토스증권 등 |
| **PB** | Private Banker | 자산관리 직원 |
| **PII** | Personally Identifiable Information | 가드레일 |

---

## 변경 이력

| 날짜 | 버전 | 변경 |
|------|------|------|
| 2026-05-10 | v0.1 | 초안 — 8 카테고리 약 100개 용어 |
