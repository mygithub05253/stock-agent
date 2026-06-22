# stock-agent AI 시스템 — 핵심 요약 (1-Pager)

> 발표·면접·온보딩용 압축본. 원본 풀세트: [모델 카드](model_card.md) · [프롬프트 명세](prompt_spec.md) · [평가 보고서](eval_report.md) · [오케스트레이션 설계](orchestration.md)
> 기준 SSOT: [11노드 그라운드 트루스](../architecture/pipeline_11node_groundtruth.md) (코드 직접 추출)

## 한 문장
사용자 투자성향·포트폴리오를 받아 **정량·정성·Peer·거시**를 LangGraph 11노드로 동적 병렬 분석하고, **결정적 합성 + Guardrail 게이트**로 안전한 BUY/HOLD/SELL 분석 신호를 내는 한국 주식 멀티에이전트.

## 모델 구성 (코드 확정)
| 모델 | 용도 | 폴백 |
|------|------|------|
| **Qwen2.5-7B** (OpenRouter) | InvestmentAnalyst 1차 합성, Competitor narrative | → GLM |
| **GLM-4.5-Flash** (Z.ai) | Curator·Classifier 구조화, Analyst 폴백 | → local-rule |
| **BGE-M3** (1024-dim) | 뉴스·공시 RAG 임베딩 (pgvector) | — |

- **3단 라우팅**: Qwen → GLM → 결정적 결과 → **키 없이도 데모 가능**.
- **결정적 영역**: Quant·Qual·Macro·Strategist·Guardrail은 LLM 미사용(재현성·안전성). *Quant·Qual 프롬프트는 향후 LLM 연결용 계약으로 보관.*
- **비용**: 월 5만원 캡 준수, sLLM 우선 라우팅.

## 오케스트레이션 한눈에
```
curator → classifier ─(Send 동적 fan-out)→ [quant · qual · competitor · (macro 조건부)]
                                                   └── join ──→ strategist → investment_analyst
                                                                 → guardrail → guardrail_apply ─(재생성 ≤2)
                                                                 → renderer → END
```
- **Send fan-out**: 필요한 워커만 병렬 실행(macro는 업종 확인 시에만).
- **부분 실패 강건**: 워커 격리 + `degraded` 진행.
- **revision loop**: 위험 표현은 차단이 아닌 재합성(최대 2회) + PII 마스킹.

## 평가 결과 (근거 기반)
| 지표 | 결과 | 목표 |
|------|------|------|
| Phase 1 rule-based | **40/41 (97.6%)** | 41/41 |
| RAGAS faithfulness | **0.41** ⚠️ | 0.80 |
| Competitor 회귀 | **6/6** | 6/6 |
| Qual RAG hit@5 / MRR / nDCG | **1.0 / 1.0 / 0.93** | — |

- **강점**: 출력 계약·규칙 준수, peer 엔진 정직성(부족·이상치 플래그), RAG 검색 적중.
- **개선 1순위**: RAG **faithfulness 0.41→0.80** — 검색은 적중하나 생성의 근거 반영이 약함(인용 스팬·context gating 강화).

## 신뢰성 설계 (왜 믿을 수 있나)
1. **Anti-hallucination 프롬프트** — 출처 없는 수치 생성 금지, 도구 계산 ↔ LLM 해석 분리.
2. **결정적 신호 + 규칙 Guardrail** — 위험 표현을 확률에 안 맡김.
3. **솔직한 평가 공개** — faithfulness 미달을 숨기지 않고 개선 대상으로 관리.

> 출력은 투자 권유가 아닌 데이터 기반 분석 신호입니다.
