# stock-agent — BDAI 12기 팀 프로젝트

> **한국 주식 투자자 의사결정 지원 멀티에이전트 시스템**
> 회원의 포트폴리오·투자성향에 맞춰 5개년 밸류에이션과 BUY/HOLD/SELL 권유를 *근거와 함께* 제공합니다.

---

## 📖 이 문서를 처음 읽는 분께

- **개발이 처음이신 팀원**: 아래 [용어 미니풀이](#-용어-미니풀이-처음-보는-사람용) 부터 보세요.
- **개발자 / 데이터팀**: [빠른 시작](#-빠른-시작) 으로 바로 환경 셋업.
- **PM / 기획**: [문서 영역](#-문서-영역-docs) 과 [협업 가이드](#-협업-가이드-반드시-읽어주세요) 만 봐도 됩니다.
- **상세 요구사항**: `docs/prd/PRD_v0.6.md` 부터 읽어주세요.

---

## 📚 용어 미니풀이 (처음 보는 사람용)

| 용어 | 한 줄 설명 |
|------|-----------|
| **에이전트(Agent)** | LLM에게 도구(검색·계산)를 주고 스스로 판단하게 만드는 단위. 우리 시스템엔 6명이 있음 |
| **LLM** | Large Language Model. GPT·Claude·Solar 같은 대화 모델 |
| **RAG** | Retrieval-Augmented Generation. "검색해서 그 결과를 바탕으로 답변" |
| **LangGraph** | 여러 에이전트를 그래프로 연결해 동작시키는 파이썬 라이브러리 |
| **Streamlit** | 파이썬으로 웹 화면을 만드는 도구. 우리 UI |
| **Postgres** | DB. 회원·종목·재무·시세 등 정형 데이터 저장 |
| **pgvector** | Postgres 안에서 뉴스·공시 임베딩을 저장하고 유사도 검색하는 확장 |
| **DART** | 금융감독원 전자공시. 한국 상장사 재무·공시 공식 데이터 출처 |
| **pykrx** | KOSPI/KOSDAQ 시세를 무료로 가져오는 파이썬 라이브러리 |
| **LangSmith** | LLM·LangGraph 호출을 추적·디버깅하는 도구 (추후 도입) |
| **PR** | Pull Request. "내 작업을 메인 코드에 합쳐달라" 요청 |
| **PM** | Project Manager. 본 레포는 PM 2명이 PR 검수·Merge 담당 |

> 더 많은 용어는 `docs/glossary.md` 를 보세요.

---

## 🎯 시스템 한눈에

### 6 에이전트
1. **Curator Agent** — 사용자 자연어 → 의도·종목 파싱 / 종목 미지정 시 후보 추천
2. **Qual Worker Agent ★** — 뉴스·공시 RAG로 호재/악재 분석 (W1+W3 핵심)
3. **Quant Worker Agent** — DART 재무 + pykrx 시세로 5y 밸류에이션 계산
4. **Competitor Agent** — 동종업계 Peer 추출 + 횡비교
5. **Strategist & Synthesizer Agent** — 4 워커 종합 → BUY/HOLD/SELL + PB 리포트
6. **Guardrail & Evaluator Agent** — 위험 표현 차단 + RAGAS 자동 채점

### 11 사용자 기능

**기본 기능 (Phase 1, 7~8주차)**: 회원가입 / 보유 종목 등록 / 종목 검색 / 종목 기본 정보 / 포트폴리오 일괄 안내
**고급 기능 (Phase 2, 9~11주차)**: 5개년 밸류에이션 / 산업·정성 분석 / 동종업계 횡비교 / BUY·HOLD·SELL 권유 / 종목 추천 (Curator) / PB 리포트 다운로드

자세한 내용은 `docs/prd/PRD_v0.6.md` 참조.

---

## 🗂 프로젝트 구조

> ⚠️ **Streamlit 표준 구조** — `streamlit_app.py` 와 `pages/` 는 반드시 루트에 위치 (Streamlit이 자동 인식).

```text
stock-agent/
│
├── streamlit_app.py               🖥 Streamlit Cloud 진입점 (홈 페이지)
├── pages/                         🖥 Streamlit 멀티페이지 (자동 인식)
│   ├── 1_분석_진행중.py
│   ├── 2_추천_결과.py
│   ├── 3_상세_산출물.py
│   └── 9_관리자_평가.py
│
├── ui/                            🖥 재사용 UI 컴포넌트 (페이지에서 import)
│   └── components/                액션 카드·근거 카드·진행 사이드바·책임고지
│
├── docs/                          📘 PM 문서 영역 (요구사항·설계·운영)
│   ├── prd/                       PRD (요구사항 정의서)
│   ├── functional-spec/           기능 명세서 (각 기능 동작)
│   ├── architecture/              시스템 설계 (흐름도·ERD·에이전트)
│   ├── operations/                운영 가이드 (LLM 비용·배포)
│   ├── decisions/                 ADR (의사결정 기록)
│   ├── glossary.md                용어집
│   └── assets/                    이미지·다이어그램 PNG
│
├── datas/                         📥 데이터 수집 (데이터팀)
│   ├── news/                      뉴스 크롤링
│   ├── macro/                     매크로 지표
│   └── dart/                      DART 재무·공시
│
├── db/                            🗄 DB 스키마
│   └── init/                      Postgres 초기화 SQL
│
├── src/stock_agent/               🤖 애플리케이션 코드 (Streamlit이 import)
│   ├── agents/                    6개 에이전트 구현
│   ├── graph/                     LangGraph 오케스트레이션
│   ├── prompts/                   LLM 프롬프트 (코드와 분리 보관)
│   ├── harness/                   횡단 컴포넌트 (가드레일·출처추적·용어풀이)
│   ├── llm/                       LLM 추상화 + 비용 라우팅
│   ├── rag/                       Postgres pgvector + Hybrid Search + Reranker
│   ├── schemas/                   Pydantic 모델
│   ├── tools/                     외부 데이터 Tool (DART·pykrx·News)
│   ├── config.py                  공통 설정
│   └── db.py                      DB 연결
│
├── eval/                          🧪 평가 하네스
│   ├── golden_set/                골든셋 (페르소나 입력·기대 결과)
│   ├── reports/                   일별 자동 평가 리포트
│   └── run_benchmark.py           평가 실행 스크립트
│
├── scripts/                       🛠 운영 스크립트 (cron·배치 분석 등)
├── tests/                         ✅ 단위·통합 테스트
│
├── Dockerfile, docker-compose.yml
├── pyproject.toml                 Python 의존성
└── .env.example                   환경 변수 예시
```

> 각 폴더 안의 `README.md` 가 더 자세한 책임·작업 규칙을 담고 있습니다.

---

## 🚀 빠른 시작

### 1. 환경 변수 준비

```bash
cp .env.example .env
```

필요한 값(API 키 등)은 `.env`에 채워 넣습니다. **`.env`는 절대 커밋하지 마세요.**

### 2. PostgreSQL 실행

```bash
docker compose up -d db
```

기본 접속 정보:
- Host: `localhost` / Port: `5432`
- Database: `stock_agent` / User: `stock_agent` / Password: `stock_agent`
- Docker에서는 `pgvector/pgvector:pg16` 이미지를 사용합니다.

기존 로컬 Docker 볼륨을 이미 만든 팀원은 새 스키마가 자동 적용되지 않을 수 있습니다. 이때는 DB를 띄운 뒤 아래 명령을 실행합니다.

```bash
python scripts/apply_db_schema.py
```

### 3. Python 개발 환경

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

의존성의 기준 파일은 `pyproject.toml`입니다. `requirements.txt`와 `requirements-dev.txt`는 팀원이 익숙한 명령으로 설치할 수 있게 둔 얇은 진입점입니다.

### 4. DB 연결 확인

```bash
python scripts/check_db.py
```

### 5. Streamlit UI 실행

```bash
streamlit run streamlit_app.py
```

브라우저가 열리며 사이드바에 `pages/` 안의 페이지들이 자동 노출됩니다 (1_분석_진행중·2_추천_결과·3_상세_산출물·9_관리자_평가).

> Streamlit 멀티페이지는 `pages/` 가 *루트* 에 있어야 자동 인식됩니다. `ui/pages/` 같은 곳에 두면 안 됨.

### Docker로 앱까지 실행

```bash
docker compose --profile app up --build
```

브라우저에서 `http://localhost:8501`을 엽니다. 현재 Phase 1은 삼성전자 1종목 기준 mock E2E입니다.

---

## 🤝 협업 가이드 (반드시 읽어주세요)

> 개발 경험이 적어도 걱정 마세요. 이 규칙은 **여러분의 작업물이 사고로 사라지는 것을 막는 안전망** 입니다.
> 모르는 게 있으면 PM에게 질문해 주세요.

### 1. 브랜치 규칙 (내 작업 공간 만들기)

`main` 코드에 직접 수정하면 안 됩니다. 무조건 본인 브랜치에서 작업:

| 브랜치 | 의미 | 직접 push 가능? |
|--------|------|-----------------|
| **`main`** | 라이브 배포용 무균실 | ❌ PM Merge만 |
| **`dev`** | 팀원 코드 합쳐서 테스트하는 놀이터 | ❌ PR Merge만 |
| **개인 작업** | `<유형>/<본인ID>-<작업내용>` | ✅ 본인만 |

**브랜치명 예시**:
- `feature/p2-crawling-naver` (P2가 네이버 크롤링 기능 추가)
- `feature/p3-quant-agent` (P3가 Quant Agent 구현)
- `docs/pm-prd-v06` (PM이 PRD v0.6 작성)
- `fix/p4-langsmith-trace` (P4가 LangSmith 트레이싱 버그 수정)

### 2. 커밋 메시지 규칙 (저장할 때 남기는 메모)

머리말(prefix)을 꼭 달아주세요. 누가 봐도 "어떤 종류의 작업"인지 알 수 있게.

| Prefix | 의미 | 예시 |
|--------|------|------|
| ✨ `Feat` | 새 기능 추가 | `✨ Feat: 네이버 뉴스 크롤링 기능 추가` |
| 🐛 `Fix` | 버그 수정 | `🐛 Fix: 차트 안 보이는 오류 해결` |
| 📝 `Docs` | 문서 수정 | `📝 Docs: PRD v0.6 작성` |
| 🎨 `Style` | 코드 정렬·디자인 (기능 변화 X) | `🎨 Style: ruff 적용` |
| ♻️ `Refactor` | 동작은 같고 구조만 변경 | `♻️ Refactor: agent 파일 분리` |
| ✅ `Test` | 테스트 추가/수정 | `✅ Test: curator 단위테스트 추가` |
| 🔧 `Chore` | 빌드·설정 변경 | `🔧 Chore: pyproject.toml 의존성 추가` |

### 3. PR (Pull Request) 규칙

내 브랜치 작업이 끝나면 `dev`(또는 `main`)에 합쳐달라고 *결재* 를 올립니다. 이게 PR.

1. **절대 혼자 Merge 금지** — PM 2명 중 1명 이상의 승인 필요
2. PR 올린 후 **단톡방에 알림** ("P3 Quant Agent PR 올렸습니다!")
3. **PR 본문에 들어가야 할 것**:
   - 무엇을 했는지 (1~3줄 요약)
   - 왜 했는지 (관련 이슈·PRD 섹션)
   - 어떻게 테스트했는지 (스크린샷·테스트 결과)
4. PM 검수 후 Merge → `dev` 에 합쳐짐
5. `dev`에서 통합 테스트 후 일정 시점에 `main` 으로 일괄 Merge

> *왜 이렇게 하나요?* 오류 코드가 라이브에 바로 올라가는 것을 막고, 서로 무슨 작업하는지 알기 위해서.

### 4. 폴더 책임 분담 (어디에 뭘 넣어야 할까?)

| 폴더 | 누가 작업? | 무엇을 넣나? |
|------|-----------|-------------|
| `datas/news/` | 데이터팀 (뉴스) | 뉴스 크롤러 + 정제 코드 |
| `datas/macro/` | 데이터팀 (매크로) | ECOS·FRED 수집 |
| `datas/dart/` | 데이터팀 (DART) | DART 재무·공시 수집 |
| `db/init/` | 데이터팀 + 백엔드 | Postgres 스키마 SQL |
| `src/stock_agent/agents/` | 에이전트 담당 | 6개 에이전트 구현 |
| `src/stock_agent/graph/` | 에이전트 담당 | LangGraph 오케스트레이션 |
| `src/stock_agent/prompts/` | 에이전트 + PM | LLM 프롬프트 (코드와 분리) |
| `src/stock_agent/rag/` | 에이전트 (RAG) | Postgres pgvector + Reranker |
| `src/stock_agent/tools/` | 에이전트 (Tool) | 외부 데이터 Tool 함수 |
| `ui/` | UI 담당 | Streamlit 페이지·컴포넌트 |
| `eval/` | 평가 담당 + PM | 골든셋·평가 스크립트 |
| `docs/` | **PM** | 모든 기획·설계·운영 문서 |

### 5. 코드 작성 규칙

#### 주석은 필수, **Why**를 적기

```python
# ❌ 나쁜 예: 리스트를 합친다.
# ✅ 좋은 예: 네이버 뉴스와 한경 뉴스의 중복을 제거하기 위해 리스트를 합친다.
```

#### 프롬프트는 코드에서 분리

LLM 프롬프트는 절대 .py 파일에 직접 쓰지 말고, `src/stock_agent/prompts/` 안의 .md 파일에 두세요. 그래야 PM·기획자도 수정할 수 있습니다.

#### 새 패키지 설치 시

```bash
pip install <package>
```
설치하셨다면 **반드시 단톡방 공유 + `pyproject.toml` 의 `dependencies` 에 추가** 해주세요. 다른 팀원이 동일하게 설치할 수 있게.

#### 환경 변수 추가 시

`.env.example` 에 키만 추가 (값은 빈칸 또는 예시). 실제 값은 본인 `.env` 에만.

---

## 🗄 데이터 저장 원칙

| 데이터 종류 | 저장소 | 이유 |
|-------------|--------|------|
| 회원·포트·재무·시세 (정형) | **Postgres** | JOIN·트랜잭션 필요 |
| 뉴스·공시 본문 + 임베딩 (비정형) | **Postgres + pgvector** | DB 1개로 벡터 유사도 검색 |
| 산출 파일 (Excel·PDF·DOCX) | 컨테이너 임시 + 사용자 다운로드 | DB BLOB 저장 금지 (Streamlit Cloud 1GB 제한) |
| 원본 PDF/HTML | 로컬 캐시 (재기동 시 재다운로드) | MVP는 단순화 |

Chroma는 삭제하지 않고 향후 optional RAG backend 후보로 남깁니다. MVP 기본 경로는 Postgres 단일 DB입니다.

자세한 내용: `docs/decisions/ADR-001-data-arch-postgres-pgvector.md`

---

## 💰 LLM 비용 정책

> **월 5만원 초과 금지** (PRD Non-goal에 명시)

핵심 패턴:
1. **모델 라우팅** — 단순 작업은 작은 모델, 복잡 결정만 큰 모델
2. **응답 캐싱** — 같은 종목 24시간 내 재분석 시 DB 캐시 사용
3. **부트캠프 무료 크레딧 (Solar)** 우선
4. **Self-Consistency N=3** (5에서 축소)

자세한 내용: `docs/operations/llm_cost_guide.md`

---

## 📘 문서 영역 (`docs/`)

PM이 주로 관리하는 문서들:

| 문서 | 내용 | 누가 읽어야? |
|------|------|--------------|
| `docs/prd/PRD_v0.6.md` | 요구사항 정의서 (Problem·Goal·Scope·User Story·Phase) | 전원 |
| `docs/functional-spec/` | 기능 명세서 (각 기능 트리거·입력·처리·출력·예외) | 개발팀 |
| `docs/architecture/system_flow.md` | 시스템 흐름도 (Mermaid) | 전원 |
| `docs/architecture/erd.md` | DB ERD | 데이터팀·백엔드 |
| `docs/architecture/agent_design.md` | 6 에이전트 상세 설계 | 에이전트 담당 |
| `docs/operations/llm_cost_guide.md` | LLM 비용 절감 가이드 | 에이전트 담당·PM |
| `docs/decisions/ADR-*.md` | 의사결정 기록 (왜 이 선택?) | 전원 (옵션) |
| `docs/glossary.md` | 용어집 | 비전공자 팀원 |

---

## 🐳 Docker 명령어 모음

```bash
# DB만 띄우기
docker compose up -d db

# DB 로그 보기
docker compose logs -f db

# 전부 내리기 (데이터 유지)
docker compose down

# 데이터까지 삭제 (⚠️ 주의)
docker compose down -v

# 앱 컨테이너 빌드 + Streamlit 실행
docker compose --profile app up --build

# 앱 컨테이너에서 DB 연결 확인
docker compose --profile app run --rm app python scripts/check_db.py
```

---

## 🆘 도움이 필요하면

- 프로젝트 전반: PM 단톡방 (#stock-agent-pm)
- 기술 이슈: GitHub Issues 활용
- 긴급 (배포·DB 장애): PM에게 직접 DM

---

## 📝 변경 이력

| 날짜 | 버전 | 변경 |
|------|------|------|
| 2026-05-10 | v1.0 | 협업 가이드 + 새 폴더 구조 + 6 에이전트 + 비전공자 용어풀이 추가 |
| (이전) | v0.1 | 데이터팀 초기 셋업 (Postgres + Docker + datas/news/macro/dart) |

---

> **본 프로젝트는 BDAI 12기 부트캠프 학습 목적이며, 시스템 출력은 투자 권유가 아닙니다.**
