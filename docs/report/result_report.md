# 결과 보고서 (Result Report) — stock-agent

> 종합 근거: [PRD](../prd/PRD_v0.6.md) · [SRS](../requirements/srs.md) · [구현 정합 매트릭스](../functional-spec/IMPLEMENTATION_STATUS.md) · [평가 보고서](../ai/eval_report.md) · [테스트 명세](../testing/test_spec.md)
> 11노드 SSOT: [`pipeline_11node_groundtruth.md`](../architecture/pipeline_11node_groundtruth.md)
> 작성: PM 문서화 트랙 (2026-06-22, 코드·평가·강사 피드백 기반)

본 보고서는 stock-agent의 **문제 → 설계 → 구현 → 평가 → 개선** 전 과정을 하나의 서사로 묶은 발표 본체입니다. 핵심 메시지는 **"D(32/70)에서 시작해 C(48/70)로 회복하고, 평가·문서 정합으로 B를 향한다"**는 개선 서사입니다.

---

## 1. 한 줄 요약

> 개인투자자(평균 −16.77%)의 *근거 없는 결정* 문제를, 11노드 멀티에이전트가 정량·정성·Peer·거시를 종합하고 Guardrail로 안전하게 분석 신호를 내는 시스템으로 해결한다. Competitor(FR-A3)는 100% 완성, 전체 파이프라인 E2E·평가 하네스·CI가 동작하며, 남은 레버는 RAG 충실도와 영속화다.

---

## 2. 문제와 목표 (Why)

- **문제**: 진입장벽은 낮아졌으나(토스 860만) 분석·근거는 정보 비대칭 → 개인투자자 2024년 평균 **−16.77%**([시장조사](../research/market_research.md)).
- **목표**(PRD §2.1): 종목 입력 시 5개년 밸류에이션 + BUY/HOLD/SELL을 **근거와 함께 60초 안에**, Streamlit Cloud 라이브로.

---

## 3. 설계 (How) — 11노드 멀티에이전트

```
curator → classifier ─(Send 동적 fan-out)→ [quant · qual · competitor · (macro)]
                                              └ join → strategist → investment_analyst
                                                       → guardrail → guardrail_apply(재합성 ≤2) → renderer
```
- **결정적 신호 + 규칙 Guardrail**: 재현성·안전성. LLM은 해석·합성만([오케스트레이션](../ai/orchestration.md)).
- **3단 LLM 라우팅**: Qwen→GLM→rule, 키 없이도 데모 가능([모델 카드](../ai/model_card.md)).
- 상세 근거: [SRS](../requirements/srs.md), [프롬프트 명세](../ai/prompt_spec.md).

---

## 4. 구현 결과 (What shipped)

### 4.1 기능 구현 현황 (매트릭스 요약)

| 구분 | ✅ 구현 | 🟡 부분 | ⚠ 설계안 |
|------|--------|---------|----------|
| 기본(B1~B5) | — | 5 | — |
| 고급(A1~A6) | **A3(100%)** | A1·A2·A4·A5 | A6 |
| 횡단 인프라 | E2E·Macro·Guardrail·Docker·CI·RAGAS·Competitor회귀·MCP | — | LangGraph전환·sLLM·스트리밍 |

- **대표 성과 FR-A3(Competitor)**: 3단 폴백·복합 유사도(#62)·이상치 플래깅·품질 회귀 골든셋·MCP 외부 노출(A2A)까지 **100% 마감**.
- **횡단 인프라**: Phase 1 E2E, Macro 연결(#49), Guardrail 실게이팅(#50), Strategist 부분실패 허용(#51), CI 게이트(#63) 모두 동작.

### 4.2 코드 검증으로 정정한 사실

- InvestmentAnalyst는 **Qwen 우선 → GLM 폴백 → rule** 3단(과거 "GLM 최종" 표기 정정).
- Quant·Qual은 프롬프트 존재하나 **LLM 미연결**(결정적 구현, 명세 계약 보관).

---

## 5. 평가 챕터 (Evidence)

| 지표 | 결과 | 목표 | 판정 |
|------|------|------|:----:|
| Phase 1 rule-based | **40/41 (97.6%)** | 41/41 | 🟢 |
| Competitor 회귀 | **6/6 (100%)** | 6/6 | 🟢 |
| RAG 검색 hit@5/MRR/nDCG | **1.0/1.0/0.93** | — | 🟢 |
| RAGAS faithfulness | **0.41** | ≥0.80 | 🔴 |
| 테스트 함수 | **137개** 통과(CI 게이트) | — | 🟢 |

- **강점**: 출력 계약·규칙 준수, Peer 엔진 정직성, RAG 검색 적중.
- **약점(1순위)**: RAG **faithfulness 0.41** — 검색은 적중하나 생성의 근거 반영이 약함. 자세한 케이스·가설은 [평가 보고서](../ai/eval_report.md) §2.1.

---

## 6. 개선 서사 (D → C → B)

| 단계 | 점수 | 상태 | 핵심 |
|------|------|------|------|
| **D** | 32/70 | 초기 재검토 | 드리프트(6→9→11노드 혼재), 항목4 캡 3(유스케이스·인터페이스 부재), 평가 미정량 |
| **C** | 48/70 | 회복 | Macro·Guardrail·Strategist·Qual 폴백 머지, Competitor MCP, RAGAS 실측 도입 |
| **B(목표)** | — | 진행 | 캡 해제(유스케이스·인터페이스 ✅), 11노드 SSOT 정합, AI 문서 풀세트, RAG 충실도 개선 |

**B를 향한 잔여 레버**:
1. 🔴 RAG faithfulness 0.41→0.80 (인용 스팬·context gating).
2. 🟠 영속화 테이블(users·holdings·analysis_cache) DDL 구현 → 기본기능 🟡→✅.
3. 🟠 LangGraph StateGraph 전환·sLLM 전환(설계안 → 구현).
4. 🟢 PB 리포트(A6) 다운로드 경로.

---

## 7. 한계와 책임 고지

- 일부 worker는 MVP mock 구간(실데이터 단계적 연결).
- 동시 사용자 ≤3, 일봉 기준, 자동매매 미지원(PRD Non-goal).
- **출력은 투자 권유가 아닌 데이터 기반 분석 신호이며, 최종 판단·책임은 사용자에게 있습니다.**

---

## 8. 부록 — 추적성

| 장 | 근거 문서 |
|----|----------|
| 문제·시장 | [market_research.md](../research/market_research.md), PRD §1 |
| 요구사항 | [srs.md](../requirements/srs.md) |
| 설계 | [orchestration.md](../ai/orchestration.md), [SSOT](../architecture/pipeline_11node_groundtruth.md) |
| 구현 | [IMPLEMENTATION_STATUS.md](../functional-spec/IMPLEMENTATION_STATUS.md) |
| 평가 | [eval_report.md](../ai/eval_report.md), [test_spec.md](../testing/test_spec.md) |

> 본 보고서는 코드·평가·피드백 변경 시 함께 갱신한다. 발표·면접용 압축본은 [AI 요약본](../ai/ai_summary_1pager.md).
