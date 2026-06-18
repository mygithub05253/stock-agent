# 기능 명세 ↔ 실제 구현 정합 매트릭스 (코드 기준)

| 항목 | 값 |
|------|-----|
| 작성자 | PM (이동원) |
| 작성일 | 2026-06-14 |
| 목적 | 강사 #4(ERD↔실제 SQL 불일치, 코드 우선) 정합 원칙을 **기능 명세 전체**로 확장. 각 기능 명세가 기술한 설계가 실제 코드에 어디까지 구현됐는지 한곳에서 추적한다. |
| 정합 기준 | **상충 시 실제 코드가 우선.** 명세 본문(트리거·입력·처리·출력·예외)은 목표 설계를 포함할 수 있으며, 본 매트릭스가 "현재 코드 상태"의 단일 출처(SSOT)다. |

> ⚠️ 본 매트릭스의 타 담당 기능(B·A1·A2·A4·A5·D1) 상태는 **코드 기준 PM 추정**이며, 정밀 확정은 각 담당의 확인이 필요하다(`담당확인` 표기). Competitor(A3)는 담당 직접 작성으로 확정 상태다.

---

## 1. 범례

| 표기 | 의미 |
|:----:|------|
| ✅ 구현 | 실제 코드 경로에서 동작(테스트/실행 확인) |
| 🟡 부분 | 일부만 구현(예: 세션 동작 O, DB 영속화 X / mock 기반) |
| ⚠ 설계안 | 명세에는 있으나 코드 미구현(향후) |
| ❌ 미구현 | 코드/DDL 없음 |

---

## 2. 기능별 구현 상태

| ID | 기능 | 주 담당 | 상태 | 코드 기준 근거 / 미구현 항목 |
|----|------|---------|:----:|------------------------------|
| B1 | 회원가입/로그인 | InvestorProfile·UI | 🟡 부분 `담당확인` | 온보딩→`UserProfile` 구조화는 동작. **`users` 테이블 DDL 미구현**(erd.md §0.1) → 계정 영속화·세션 인증은 미구현 |
| B2 | 보유 종목 등록/조회 | Curator·UI | 🟡 부분 `담당확인` | Streamlit 포트폴리오 입력은 동작(`tests/test_streamlit_intake.py`). **`holdings` DDL 미구현** → DB 영속화 없음(세션 보관) |
| B3 | 종목 검색 | Curator | 🟡 부분 `담당확인` | Curator의 종목/후보 큐레이션·corp_code 보정 동작. 전체 universe 검색 UI는 부분 |
| B4 | 종목 기본 정보 조회 | Curator·Quant | 🟡 부분 `담당확인` | `company`·`stock_price` 실데이터 경로 존재, 일부 mock 폴백 |
| B5 | 포트폴리오 일괄 안내 | Strategist | 🟡 부분 `담당확인` | Strategist 종합·부분실패 허용(#51) 동작. 다수 종목 일괄 UI는 부분 |
| A1 | 5개년 밸류에이션 | Quant | 🟡 부분 `담당확인` | Quant 재무·시세 계산·fallback(#53). MVP 3개년 기준, 5개년 확장 전 |
| A2 | 산업·정성 분석 | Qual | 🟡 부분 `담당확인` | Qual RAG + try/except 폴백(#52). Hybrid/Reranker는 pgvector 단독(미고도화, #9) |
| **A3** | **동종업계 횡비교** | **Competitor (이동원)** | **✅ 구현(100%)** | **3단 폴백(DB→MCP 실시간→mock)·복합 유사도(#62)·이상치 플래깅·품질 회귀 골든셋·MCP 외부 노출. 미구현: `analysis_cache`·manual peer·Heatmap** → A3 명세 §0.1 |
| A4 | BUY/HOLD/SELL 신호 | Strategist·Guardrail | 🟡 부분 `담당확인` | 신호 생성·Guardrail 게이팅(#50) 동작. 전 케이스 HOLD 변별력은 과제 |
| A5 | 종목 추천 | Curator | 🟡 부분 `담당확인` | Curator 후보 반환 동작. 추천 랭킹 고도화는 부분 |
| A6 | PB 리포트 다운로드 | Strategist·UI | ⚠ 설계안 | 명세 예정, 산출 파일 다운로드 경로 미구현 |
| D1 | 백테스팅 예측 검증 데모 | PM·개발팀 | ⚠ 설계안 | `backtesting_demo_architecture.md` 설계 존재, 자동화 경로는 데모 수준 |

---

## 3. 횡단 인프라 구현 상태 (전 기능 공통)

| 항목 | 상태 | 근거 |
|------|:----:|------|
| Phase 1 E2E 파이프라인 | ✅ 구현 | `Curator→Quant/Qual/Competitor→Strategist→InvestmentAnalyst→Guardrail` |
| Macro 파이프라인 연결 | ✅ 구현 | `run_macro` + Strategist 가중 소비(#49) |
| Guardrail 실게이팅 | ✅ 구현 | 7게이트 `passed=not blocked`(#50) |
| Docker 실행 | ✅ 구현 | `docker compose --profile app` |
| CI 게이트 | ✅ 구현 | compileall + pytest + 충돌마커(#63) |
| RAGAS 정량 평가 | ✅ 구현 | `eval/run_benchmark.py`(faithfulness·context_precision) |
| Competitor 품질 회귀 | ✅ 구현 | `eval/run_competitor_eval.py` |
| MCP / A2A | ✅ 구현 | Competitor `mcp_bridge` 외부 노출 |
| **LangGraph StateGraph 전환** | ⚠ 설계안 | `pipeline.py` 순차 호출(#1, Graph 담당) |
| **오픈웨이트 sLLM** | ⚠ 설계안 | OpenRouter 기본 gpt-4o-mini(#3) |
| 스트리밍·비동기 | ⚠ 설계안 | `st.write_stream`·`asyncio.gather` 미적용(#10) |
| 영속화 테이블(users·holdings·analysis_history·analysis_cache) | ❌ 미구현 | DDL 없음(erd.md §0.1) |
| `llm_cost_log` 기반 월 비용 단계 제어 | ❌ 미구현 | 키 부재 시 LLM 생략만 구현 |

---

## 4. 운영 원칙

- 명세서를 수정할 때 본 매트릭스도 함께 갱신한다(명세 ↔ 코드 드리프트 방지).
- `담당확인` 항목은 단톡방 공유 후 각 담당이 자기 기능 행을 확정한다.
- 신규 기능 머지 시 해당 행 상태를 ✅로 승격하고 근거(파일·PR)를 남긴다.

## 5. 변경 이력

| 날짜 | 변경 |
|------|------|
| 2026-06-14 | 기능 명세 전체 구현 정합 매트릭스 신설. A3 ✅ 확정, 나머지는 코드 기준 추정(담당확인) |
