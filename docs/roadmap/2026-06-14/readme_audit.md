# README 정합 감사 — 2026-06-14

> 작성: PM(이동원). 전 폴더 README와 실제 코드/구조를 대조해 드리프트를 정리한다.
> **폴더 책임 분담 원칙**에 따라 PM 영역(루트 README·`docs/`)과 Competitor 영역만 본 작업에서 직접 수정하고,
> 타 담당 영역(`datas/`·타 `agents/`·`rag/`·`ui/`·`graph/`)은 아래 표로 조율용 기록만 남긴다(담당자 PR로 반영 요청).

## 요약

| 영역 | 상태 | 조치 |
|------|:----:|------|
| 루트 `README.md` | ⚠ 드리프트 | **PM이 직접 수정**(본 세션) |
| `src/stock_agent/tools/README.md` | ✅ 정합 | 회귀 평가 참조 추가(완료) |
| `src/stock_agent/mcp_bridge/README.md` | ✅ 정합 | 외부 노출 섹션 추가(완료) |
| `eval/README.md` | ✅ 정합 | Competitor 회귀 섹션 추가(완료) |
| `docs/agents/competitor_agent_mvp.md` | ✅ 정합 | 3단 폴백·회귀평가 현행화(완료) |
| `src/stock_agent/agents/README.md` | ⚠ 드리프트 | Competitor 항목만 PM 정정, 나머지는 담당 조율 |
| `pages/README.md` | ✅ 정합 | (UI) 예정 페이지로 정직하게 표기됨 |
| `src/stock_agent/graph/README.md` | ⚠ 경미 | (Graph) 에이전트 수 표기 |
| `datas/*`·`db`·`rag`·`schemas`·`harness`·`llm`·`prompts`·`ui` README | 🔎 미정밀 | 담당자 자체 점검 권장 |

---

## 1. 루트 `README.md` (PM 직접 수정)

| # | 위치 | 현재 서술 | 실제 | 조치 |
|---|------|-----------|------|------|
| 1 | 프로젝트 구조 79–83행, 251행 | `pages/`에 `1_분석_진행중.py` 등 4개 페이지가 존재·사이드바 자동 노출 | `pages/`엔 `.gitkeep`·`README.md`뿐(페이지 미작성). `pages/README.md`는 "예정"으로 정직 표기 | **수정**: "예정(7~8주차)"으로 표기 정정 |
| 2 | eval 구조 125–128행 | `run_benchmark.py`만 명시 | `run_competitor_eval.py`·`competitor_golden/` 추가됨 | **수정**: 항목 보강 |
| 3 | 문서 영역 표 | 최신이 06-13 대시보드 | 06-14 대시보드·ERD/기능명세/Competitor HTML 추가 | **수정**: 06-14 항목 추가 |
| 4 | 주요 에이전트 57행 | Competitor "현재 MVP mock" | DB→MCP 실시간→mock 3단 폴백(실데이터 우선) | **수정**: Competitor 표기 |

> 참고(타 영역): "주요 에이전트"의 Quant·Qual "MVP mock" 표기, 곳곳의 "6개 에이전트"(실제 10개 모듈) 표기는
> 에이전트/Graph 담당 영역과 얽혀 있어 PM 단독 정정 대신 담당 합의 후 일괄 정정 권장.

## 2. `src/stock_agent/agents/README.md` (Competitor 항목만 PM 정정)

- 5행 "현재 Phase 1은 mock 함수 기반으로 동작" → Macro 연결·Qual 폴백·Guardrail 게이팅·Competitor 실데이터 등으로 부분적으로 실동작. (담당 합의 정정 권장)
- 75행 "Competitor: peer DB 연결 실패 시 mock peer 비교와 warning을 반환" → **실제는 DB 실패 시 ① MCP 실시간 시세 → ② mock 순.** ← **Competitor 담당(PM) 직접 정정**.
- 그 외 책임 경계·작업 규칙은 정합.

## 3. 타 담당 영역 (담당자 점검 요청 — 직접 수정하지 않음)

| 폴더 | 비고 |
|------|------|
| `src/stock_agent/graph/README.md` | "6개 에이전트" 표기(실제 10 모듈), 목표 StateGraph 미전환 상태는 정확. 에이전트 수만 갱신 권장(Graph 담당) |
| `pages/README.md` | 예정 페이지로 정직 표기 — 드리프트 아님. 루트 README와의 불일치는 루트 쪽을 고쳐 해소 |
| `datas/{news,macro,dart}/README.md` | 수집 스크립트·적재 건수 최신성 데이터팀 자체 점검 권장 |
| `rag`·`schemas`·`harness`·`llm`·`prompts`·`ui`·`db` README | 본 세션 정밀 대조 미수행. 각 담당 자체 점검 권장 |

---

## 후속 (PM)

- 본 리포트의 "담당 조율" 항목은 단톡방 공유 후 각 담당 PR로 반영.
- 루트 README 에이전트 수(6→실제 모듈 수) 표기는 Graph/에이전트 담당과 합의해 일괄 정정.
