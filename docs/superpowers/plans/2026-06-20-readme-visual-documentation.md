# README and Visual Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 프로젝트의 목적, 실행법, 구조, 검증 성과를 루트와 각 책임 폴더에서 정확히 이해할 수 있는 README 체계와 대표 시각 자산을 완성한다.

**Architecture:** 루트 README는 방문자를 위한 제품 소개와 실행 진입점으로 재구성하고, 폴더 README는 실행 책임이 있는 상세형과 자료 탐색을 위한 인덱스형으로 나눈다. 시스템 구조의 정확성은 Mermaid 원본이 담당하고, GPT Image 2.0 생성 이미지는 README의 시각적 진입점으로 사용한다.

**Tech Stack:** Markdown, Mermaid, Streamlit, Python 3.11, LangGraph, PostgreSQL/pgvector, GPT Image 2.0, pytest

---

### Task 1: 시각 자료의 사실 기준 수집

**Files:**
- Create: `docs/assets/readme/current-streamlit-onboarding.png`
- Create: `docs/assets/readme/current-streamlit-results.png`
- Create: `docs/architecture/readme_system_architecture.md`

- [ ] **Step 1: 실행 중인 앱의 첫 화면을 캡처한다**

브라우저에서 `http://localhost:8501`을 열고 페이지 제목, 의미 있는 DOM, 콘솔 오류 부재를 확인한 뒤 1280x720 viewport를 PNG로 저장한다.

- [ ] **Step 2: 온보딩과 포트폴리오 입력을 완료한다**

7개 질문의 기본 응답을 순서대로 제출하고 기본 보유 종목과 현금을 입력해 분석 결과 화면으로 이동한다. 각 클릭 전 locator가 한 개임을 확인한다.

- [ ] **Step 3: 결과 화면을 캡처한다**

Tier 1 판단, Agent 진행 상태, 근거 탭이 보이는 상태를 `current-streamlit-results.png`로 저장하고 콘솔 오류를 다시 확인한다.

- [ ] **Step 4: 현재 구현 기준 Mermaid를 작성한다**

`readme_system_architecture.md`에 다음 노드를 포함한 `flowchart LR`를 작성한다: Streamlit UI, Intake, Curator, RequestClassifier, Quant, Qual, Competitor, Macro, Strategist, InvestmentAnalyst, Guardrail, ResultRenderer, PostgreSQL/pgvector, DART/pykrx/뉴스/매크로 소스.

- [ ] **Step 5: Mermaid 문법과 구현 정합성을 확인한다**

Run: `rg -n "flowchart|Streamlit|Curator|Quant|Qual|Competitor|Macro|Strategist|Guardrail|PostgreSQL" docs/architecture/readme_system_architecture.md`

Expected: 모든 핵심 노드가 한 번 이상 출력된다.

### Task 2: GPT Image 2.0 대표 자산 제작

**Files:**
- Create: `docs/assets/readme/stock-agent-thumbnail.png`
- Create: `docs/assets/readme/stock-agent-architecture.png`

- [ ] **Step 1: 썸네일을 생성한다**

기본 이미지 생성 도구에 현재 Streamlit 캡처를 참고 이미지로 제공한다. 가로형 한국 주식 분석 제품, 절제된 navy/blue/teal 팔레트, 포트폴리오 카드와 협업 Agent 흐름, 긴 문장·로고·워터마크 제외 조건을 사용한다.

- [ ] **Step 2: 썸네일을 프로젝트로 이동한다**

생성 결과를 `docs/assets/readme/stock-agent-thumbnail.png`에 저장하고 이미지 크기와 열기 성공 여부를 확인한다.

- [ ] **Step 3: 아키텍처 이미지를 생성한다**

Mermaid 구조를 시각 참조로 사용해 외부 데이터 -> PostgreSQL/pgvector -> 전문 Agent -> 종합/안전 검증 -> Streamlit 결과의 5단 흐름이 보이는 가로형 인포그래픽을 생성한다. 라벨은 짧은 영문 또는 검증 가능한 고유명사만 사용한다.

- [ ] **Step 4: 아키텍처 이미지를 프로젝트로 이동한다**

생성 결과를 `docs/assets/readme/stock-agent-architecture.png`에 저장한다.

- [ ] **Step 5: 두 이미지를 직접 검수한다**

각 이미지를 열어 잘림, 워터마크, 오탈자, 읽기 어려운 라벨, 프로젝트와 무관한 금융 표현이 없는지 확인한다. 문제가 있으면 한 가지 수정 사항만 지정해 재생성한다.

### Task 3: 루트 README 재구성

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 상단 제품 소개를 작성한다**

프로젝트명, 한 줄 설명, Python/Streamlit/PostgreSQL/pytest/license 배지, `stock-agent-thumbnail.png`, What/Why, 핵심 기능 3줄을 첫 화면에 배치한다.

- [ ] **Step 2: 기술 스택 표와 실행법을 작성한다**

언어, UI, 오케스트레이션, 검증 모델, DB/RAG, 데이터, 평가, 인프라를 표로 정리한다. 실행 명령에는 `git clone`, Windows와 POSIX 가상환경 활성화, `pip install -r requirements-dev.txt`, `scripts/run_local_streamlit.sh`, 직접 실행 대안 `python -m streamlit run streamlit_app.py`를 포함한다.

- [ ] **Step 3: 아키텍처와 성과 표를 작성한다**

`stock-agent-architecture.png`와 Mermaid 원본 링크를 넣고 40/41, 6/6, 5개 골든셋, 7단계 온보딩, 9개 진행 Agent를 출처 링크와 함께 표기한다. RAGAS 0.4096은 목표 0.80 미달로 명시한다.

- [ ] **Step 4: 디렉토리 구조를 현재 파일 기준으로 갱신한다**

존재하지 않는 예정 페이지는 예정으로 표시하고 `mcp_bridge`, `eval/competitor_golden`, 새 시각 자료 경로를 반영한다.

- [ ] **Step 5: 기존 운영 섹션을 보존한다**

용어 풀이, 구현 상태, 협업 가이드, 데이터 저장 원칙, LLM 비용 정책, 문서 영역, Docker 명령, 도움말, 변경 이력을 유지하고 상단 목차 흐름과 중복만 정리한다.

### Task 4: 실행 책임 폴더 README 보강

**Files:**
- Create: `datas/README.md`
- Create: `db/README.md`
- Create: `db/init/README.md`
- Create: `scripts/README.md`
- Create: `src/README.md`
- Create: `src/stock_agent/README.md`
- Create: `tests/README.md`
- Create: `tests/agents/README.md`
- Create: `tests/llm/README.md`
- Create: `tests/mcp_bridge/README.md`
- Create: `tests/rag/README.md`
- Create: `tests/tools/README.md`
- Create: `ui/components/README.md`
- Modify: `datas/dart/README.md`
- Modify: `datas/macro/README.md`
- Modify: `datas/news/README.md`
- Modify: `eval/README.md`
- Modify: `pages/README.md`
- Modify: `ui/README.md`
- Modify: `src/stock_agent/agents/README.md`
- Modify: `src/stock_agent/graph/README.md`
- Modify: `src/stock_agent/harness/README.md`
- Modify: `src/stock_agent/llm/README.md`
- Modify: `src/stock_agent/mcp_bridge/README.md`
- Modify: `src/stock_agent/prompts/README.md`
- Modify: `src/stock_agent/rag/README.md`
- Modify: `src/stock_agent/schemas/README.md`
- Modify: `src/stock_agent/tools/README.md`

- [ ] **Step 1: 새 상세형 README를 작성한다**

각 파일에 한 줄 설명, What/Why, 핵심 기능, 기술 스택, 동작 원리, 아키텍처, 검증 방법 또는 성과, 디렉토리 구조를 넣는다. 빈 폴더나 예정 기능은 실제 구현처럼 표현하지 않는다.

- [ ] **Step 2: 기존 README의 누락 섹션을 보강한다**

기존 설명과 담당 규칙은 보존하면서 기술 스택, 동작 원리, 검증, 구조 섹션을 추가한다. 코드와 충돌하는 Agent 수나 mock 상태는 현재 구현을 기준으로 바로잡는다.

- [ ] **Step 3: 기술 경계 링크를 연결한다**

Agent -> schemas/tools/prompts, Qual -> rag, Competitor -> mcp_bridge, eval -> reports/golden_set 관계를 상대 링크로 연결한다.

### Task 5: 자료·문서 폴더 인덱스 README 작성

**Files:**
- Modify: `docs/README.md`
- Modify: `docs/feedback/README.md`
- Modify: `docs/functional-spec/README.md`
- Modify: `eval/golden_set/README.md`
- Create: `docs/agents/README.md`
- Create: `docs/architecture/README.md`
- Create: `docs/assets/README.md`
- Create: `docs/assets/readme/README.md`
- Create: `docs/decisions/README.md`
- Create: `docs/functional-spec/advanced/README.md`
- Create: `docs/functional-spec/basic/README.md`
- Create: `docs/functional-spec/demo/README.md`
- Create: `docs/functional-spec/overview/README.md`
- Create: `docs/guides/README.md`
- Create: `docs/guides/2026-06-13/README.md`
- Create: `docs/guides/2026-06-13/img/README.md`
- Create: `docs/notion/README.md`
- Create: `docs/notion/images/README.md`
- Create: `docs/operations/README.md`
- Create: `docs/prd/README.md`
- Create: `docs/presentation/README.md`
- Create: `docs/roadmap/README.md`
- Create: `docs/roadmap/2026-05-23/README.md`
- Create: `docs/roadmap/2026-06-12/README.md`
- Create: `docs/roadmap/2026-06-13/README.md`
- Create: `docs/roadmap/2026-06-14/README.md`
- Create: `docs/superpowers/README.md`
- Create: `docs/superpowers/plans/README.md`
- Create: `docs/superpowers/specs/README.md`
- Create: `eval/competitor_golden/README.md`
- Create: `eval/reports/README.md`
- Create: `notebooks/README.md`
- Create: `src/stock_agent/prompts/competitor/README.md`
- Create: `src/stock_agent/prompts/curator/README.md`
- Create: `src/stock_agent/prompts/investment_analyst/README.md`
- Create: `src/stock_agent/prompts/qual/README.md`
- Create: `src/stock_agent/prompts/quant/README.md`
- Create: `src/stock_agent/prompts/request_classifier/README.md`

- [ ] **Step 1: 각 인덱스의 목적과 파일 목록을 작성한다**

폴더가 답하는 질문, 현재 주요 파일, 갱신 규칙, 관련 상위 문서를 짧게 기록한다. 날짜 폴더는 해당 날짜 산출물과 역사적 상태라는 점을 명시한다.

- [ ] **Step 2: 상·하위 README 링크를 연결한다**

각 인덱스에 상위 README 링크를 넣고, 상위 문서에는 주요 하위 인덱스 링크를 추가한다.

- [ ] **Step 3: 기존 문서 인덱스를 보강한다**

`docs/README.md`, `docs/feedback/README.md`, `docs/functional-spec/README.md`, `eval/golden_set/README.md`의 기존 규칙은 유지하고 한 줄 설명, 사용 기술 또는 형식, 동작·갱신 원리, 주요 결과, 실제 디렉토리 구조를 추가한다.

### Task 6: Streamlit UI 개선 제안 작성

**Files:**
- Create: `docs/guides/streamlit_ui_improvement_proposal.md`
- Modify: `docs/README.md`
- Modify: `ui/README.md`

- [ ] **Step 1: 현재 화면의 근거를 기록한다**

첫 화면의 넓은 빈 공간, 분산된 행동 버튼, 기본 선택 상태, 제품 가치 설명 부족과 결과 화면의 핵심 판단 위치를 캡처 기준으로 설명한다.

- [ ] **Step 2: 개선안을 우선순위로 정리한다**

P0는 첫 viewport의 가치·진행 상태·주요 CTA, P1은 질문 카드와 결과 정보 위계, P2는 Agent 상태와 근거 탭 시각화로 나눈다. 각 항목에 Streamlit 구현 수단과 제약을 함께 적는다.

- [ ] **Step 3: 관련 README에서 제안 문서를 연결한다**

`docs/README.md`와 `ui/README.md`에 상대 링크를 추가한다.

### Task 7: 문서와 애플리케이션 검증

**Files:**
- Modify: `README.md` and README files found defective during validation

- [ ] **Step 1: 관리 대상 폴더 README 존재 여부를 검사한다**

Run: PowerShell로 `git ls-files`의 모든 비숨김 부모 폴더와 새 상위 책임 폴더를 열거하고 `README.md`가 없는 폴더를 출력한다.

Expected: 출력 없음.

- [ ] **Step 2: 로컬 Markdown 링크를 검사한다**

Run: README 파일의 상대 링크와 이미지 경로를 추출해 대상 파일 존재 여부를 확인한다.

Expected: 깨진 로컬 링크 0개.

- [ ] **Step 3: Markdown 품질을 검사한다**

Run: `git diff --check`

Expected: 출력 없음, exit code 0.

- [ ] **Step 4: 전체 테스트를 실행한다**

Run: `python -m pytest`

Expected: 기존 스킵을 제외한 테스트 통과. 실패가 문서 변경과 무관하면 해당 원인을 분리해 기록한다.

- [ ] **Step 5: 데스크톱과 모바일 UI를 재검증한다**

Browser에서 1280x720과 모바일 viewport를 사용해 페이지 정체성, 의미 있는 콘텐츠, 오류 오버레이 부재, 콘솔 상태, 다음 버튼 상호작용을 확인한다.

- [ ] **Step 6: 변경 범위를 최종 검토한다**

Run: `git status --short`와 `git diff --stat`

Expected: README, 설계·계획, 문서용 이미지, UI 개선 제안만 변경되고 `scripts/run_local_streamlit.sh`는 사용자 변경으로 분리되어 있다.

### Task 8: 문서 변경 커밋

**Files:**
- Stage: 이 계획에서 생성·수정한 문서와 이미지
- Exclude: `scripts/run_local_streamlit.sh`

- [ ] **Step 1: 계획 대상 파일만 스테이징한다**

`scripts/run_local_streamlit.sh`를 제외하고 README, `docs/architecture/readme_system_architecture.md`, `docs/guides/streamlit_ui_improvement_proposal.md`, `docs/assets/readme/*.png`만 추가한다.

- [ ] **Step 2: staged diff를 확인한다**

Run: `git diff --cached --check`와 `git diff --cached --stat`

Expected: 공백 오류가 없고 사용자 변경 파일이 staged 목록에 없다.

- [ ] **Step 3: 문서 커밋을 생성한다**

Run: `git commit -m "📝 Docs: README와 프로젝트 시각 자료 전면 보강"`

Expected: 문서와 시각 자산만 포함한 커밋 생성.
