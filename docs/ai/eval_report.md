# 평가 보고서 (Evaluation Report) — stock-agent

> 기준 데이터: `eval/reports/2026-06-12_benchmark.(md|json)`, `eval/reports/2026-06-20_competitor_eval.(md|json)`, `eval/reports/2026-06-20_rag_retriever_eval.json`
> 평가 코드: `eval/run_benchmark.py`(rule-based + RAGAS), `eval/run_competitor_eval.py`(순수 엔진, 비용 0)
> 작성: PM 문서화 트랙 (2026-06-20, 리포트 수치 인용 · 결과 미수정)

본 보고서는 `eval/reports/`의 기계 판독용 수치를 **사람이 읽는 결과 서사**로 승격한 것입니다. 결과는 손으로 고치지 않고, 입력·평가 코드를 고쳐 재생성하는 원칙을 따릅니다(`eval/reports/README.md`).

---

## 1. 한눈에 보는 결과

| 평가 | 날짜 | 핵심 지표 | 결과 | 목표 |
|------|------|-----------|------|------|
| Phase 1 파이프라인 (rule-based) | 2026-06-12 | 규칙 통과 | **40/41 (97.6%)** | 41/41 |
| Phase 1 RAGAS | 2026-06-12 | faithfulness | **0.4096** | ≥ 0.80 |
| Competitor peer 회귀 | 2026-06-20 | 케이스 통과 | **6/6 (100%)** | 6/6 |
| Qual RAG 검색 | 2026-06-20 | hit_rate / MRR / nDCG@5 | **1.00 / 1.00 / 0.926** | — |

**해석 요약**: 출력 계약·규칙 준수와 Competitor 엔진·RAG 검색 적중은 우수. **RAGAS faithfulness만 목표 미달** → RAG 근거 충실도가 최우선 개선 레버.

---

## 2. Phase 1 파이프라인 벤치마크 (2026-06-12)

5개 페르소나 골든셋(`eval/golden_set/`)에 대한 rule-based 계약 검증 + RAGAS faithfulness.

| 케이스 | 페르소나 | signal / conf / suit | intent / urgency | rule | faithfulness |
|---|---|---|---|---|---|
| park_minho_hold_review | 40대 보수, 삼성전자 장기보유 | HOLD / 65 / 40 | holding_review / general | **8/8** | 0.467 |
| kim_jiyeon_buy_more | 30대 공격, SK하이닉스 추가매수 | HOLD / 75 / 65 | holding_review / general | **8/8** | 0.286 |
| lee_seojun_portfolio_review | 20대 초보, 포트폴리오 점검 | HOLD / 68 / 58 | portfolio_review / general | **7/8** ⚠️ | 0.545 |
| choi_eunseo_sell_decision | 50대 보수, 급락 손절 고민 | HOLD / 65 / 30 | sell_decision / drop | **9/9** | 0.333 |
| jung_hana_news_check | 30대 중립, 공시 이슈 확인 | HOLD / 68 / 60 | holding_review / news | **8/8** | 0.417 |

- **유일한 실패**: `lee_seojun_portfolio_review`의 `candidates_present` (포트폴리오 점검에서 추천 후보 미생성) → Curator candidates 보강 과제.
- **suitability 분리 확인**: 동일 HOLD라도 보수형 급락 케이스(choi, suit 30)와 공격형(kim, suit 65)이 적합도로 차별화 → InvestmentAnalyst 제약(종목 매력도 vs 적합도 분리)이 동작.
- **RAGAS faithfulness 0.4096(평균)**: 생성 근거가 검색 컨텍스트를 부분적으로만 반영. 케이스별 0.286~0.545로 편차 큼.

### 2.1 faithfulness 미달 원인 가설과 개선 레버

1. **Qual 근거 인용 밀도 부족** — 결정적 요약이 원문 인용을 충분히 끌어오지 못함 → 인용 스팬 강화.
2. **Self-Consistency 축소(N=3)** — 비용캡 절충으로 변동성 존재.
3. **검색→생성 정렬** — 검색은 적중(아래 §4 hit_rate 1.0)하나 생성이 이를 덜 반영 → context_precision/recall 게이팅 강화([#60] context_precision 추가).

---

## 3. Competitor peer 비교 회귀 (2026-06-20) — 6/6

LLM·DB·네트워크 미사용 **순수 엔진** 회귀(비용 0). peer 선정·상대위치 점수·플래그 로직 검증.

| 케이스 | 검증 포인트 | score | 플래그 |
|---|---|---|---|
| C1 정상 비교 | 시총·지표 근접 peer 3개 | 54 | — |
| C2 시총 band 거름 | 4배 초과 대형 peer 제외 → 부족 경고 | 61 | `peer_count_below_minimum` |
| C3 이상치 표기 | 중앙값 10배↑ PER에 outlier 부여 | 64 | `outlier_per` |
| C4 비교군 없음 | peer 0 → score 0 | 0 | `no_comparable_peers`, `peer_count_below_minimum` |
| C5 저품질 타깃 캡 | 완성도 60 미만 → score 55 상한 | 49 | `target_data_quality_low` |
| C6 복합 유사도 정렬(#62) | 시총·사업경제성 동일 시 데이터완성도만 높은 peer보다 우선 | 61 | — |

- **의미**: peer 부족·이상치·저품질을 **점수와 플래그로 정직하게 노출**(과신 방지). [#62] 복합 유사도 고도화가 정렬 회귀로 고정됨.

---

## 4. Qual RAG 검색 평가 (2026-06-20)

Hybrid RRF 검색 품질(`rag_retriever_eval.json`, k=5, 2케이스).

| 케이스 | 질의 | hit@5 | MRR | nDCG@5 | 방식 |
|---|---|---|---|---|---|
| samsung_semiconductor_risk | 삼성전자 반도체 실적 리스크 | ✅ | 1.00 | 1.00 | hybrid_rrf |
| sk_hynix_hbm | SK하이닉스 HBM AI 수요 | ✅ | 1.00 | 0.853 | hybrid_rrf |

- **요약**: hit_rate 1.0 / MRR 1.0 / nDCG@5 0.926 — **검색 자체는 정답을 상위에 안정적으로 회수**. 따라서 §2의 faithfulness 미달은 "검색 실패"가 아니라 "생성의 근거 반영" 문제로 좁혀짐.

---

## 5. 결론과 다음 액션

| 우선순위 | 액션 | 근거 |
|---|---|---|
| 🔴 1 | RAG faithfulness 0.41→0.80: 인용 스팬·context gating 강화 | §2.1 |
| 🟠 2 | `candidates_present` 실패 해소: portfolio_review 후보 생성 | §2 lee_seojun |
| 🟢 3 | Competitor/RAG 회귀 게이트 CI 상시화 유지 | §3·§4 |

> 본 보고서는 신규 리포트 생성 시 함께 갱신합니다. 발표·면접용 압축본은 [AI 문서 요약본](ai_summary_1pager.md)을 사용하세요.
