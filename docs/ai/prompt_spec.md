# 프롬프트 명세서 (Prompt Specification) — stock-agent

> 기준 코드: `src/stock_agent/prompts/*/system.md`, `src/stock_agent/agents/*.py`, `src/stock_agent/schemas/`
> 기준 SSOT: [`docs/architecture/pipeline_11node_groundtruth.md`](../architecture/pipeline_11node_groundtruth.md)
> 연계: [인터페이스 명세서](../interface/interface_spec.md)의 AI 판 — 프롬프트는 LLM 노드의 입출력 계약입니다.
> 작성: PM 문서화 트랙 (2026-06-20, 코드 읽기 기반 · 코드 미수정)

## 0. 공통 원칙 (`prompts/README.md` 작성 규칙)

1. 출처 없는 숫자·사실 생성 금지 (anti-hallucination).
2. **도구(Tool) 계산과 LLM 해석을 분리** — 숫자는 Python이 계산, LLM은 해석만.
3. BUY/HOLD/SELL은 투자 권유가 아닌 **분석 신호**로 표현.
4. 출력 키·값 범위를 parser·Pydantic schema와 일치.
5. 모든 LLM 응답은 **순수 JSON object만** (마크다운 펜스·인사말 금지).

> 검증 흐름: `system.md → Agent → llm client → Pydantic validation → eval regression` (`prompts/README.md`).

## 0.1 프롬프트 연결 상태 (코드 검증)

| 프롬프트 | 연결 Agent | LLM 호출 | 모델 | 상태 |
|---|---|---|---|---|
| `curator/system.md` | Curator | ✅ | GLM-4.5-flash | 운영 |
| `request_classifier/system.md` | RequestClassifier | ✅ | GLM-4.5-flash | 운영 |
| `competitor/system.md` | Competitor | ✅ (narrative) | Qwen-2.5-7b | 운영 |
| `investment_analyst/system.md` | InvestmentAnalyst | ✅ | Qwen→GLM | 운영 |
| `quant/system.md` | Quant | ❌ | — | **명세만** (결정적 구현, 향후 LLM 연결 대비 계약) |
| `qual/system.md` | Qual | ❌ | — | **명세만** (결정적+RAG 구현) |

---

## 1. Curator (`prompts/curator/system.md`)

- **역할**: 질의·프로필·포트폴리오 → 분석 대상 1종목 선정.
- **입력**: `user_query`, `user_profile`, `portfolio`.
- **출력 계약 (JSON)**:

| 키 | 타입 | 비고 |
|---|---|---|
| `intent` | enum | 포트폴리오 전체 점검 / 보유 종목 판단 지원 / 신규 관심 종목 점검 |
| `corp_name` | string | 기업명 |
| `stock_code` | string | 6자리 종목코드 |
| `corp_code` | string\|null | DART corp_code |
| `sector` | string | 섹터명 또는 `미분류` |
| `candidates` | string[] | 후보 기업명 |
| `warnings` | string[] | 경고 문장 |

- **핵심 제약**: 포트폴리오·프로필 우선 반영, 질의 명시 보유종목 우선, 불명확 시 빈 필드 대신 `미분류`/`null`.

## 2. RequestClassifier (`prompts/request_classifier/system.md`)

- **역할**: 의도·대상·범위·긴급도·깊이 구조화 (→ worker_plan 결정의 입력).
- **출력 계약 (JSON)**:

| 키 | 값 범위 |
|---|---|
| `intent` | `holding_review` \| `new_recommendation` \| `risk_review` \| `sell_decision` \| `portfolio_review` |
| `target_stock_code` | 6자리 또는 null |
| `target_corp_name` | 기업명 또는 null |
| `target_sector` | 산업명 또는 null |
| `analysis_scope` | `single_stock` \| `portfolio` \| `sector` |
| `urgency_reason` | `surge` \| `drop` \| `earnings` \| `news` \| `general` |
| `requested_depth` | `summary` \| `standard` \| `deep` |

- **오케스트레이션 영향**: `analysis_scope`는 [오케스트레이션 설계서](orchestration.md)의 macro 조건부 실행 분기를 좌우합니다.

## 3. Quant (`prompts/quant/system.md`) — *명세만, LLM 미연결*

- **역할(설계)**: `QuantCalculatedMetrics` JSON을 읽어 정량 분석(이유·리스크) 서술.
- **출력 계약**: `{ "reasons": [...], "risks": [...] }`.
- **CRITICAL 제약**: 숫자 직접 계산·추정 금지(도구 계산값만), 결측(null)은 "데이터 부족으로 산출 불가" 명시, 투자 권유 표현 금지, 최종 BUY/HOLD/SELL 미결정.
- **현재**: `quant.py`는 도구 계산 결과를 결정적으로 가공. 이 프롬프트는 LLM 연결 시 적용할 계약으로 보관.

## 4. Qual (`prompts/qual/system.md`) — *명세만, LLM 미연결*

- **역할(설계)**: 공시 원문 리스트 → 호재/악재 sentiment·event 판별.
- **출력 계약**: `{ "score": 0-100, "sentiment": "positive|neutral|negative", "event_types": [...], "evidence": [≤3], "risks": [≤3] }`.
- **핵심 제약**: 공시에 없는 사실 유추 금지, 단순 정기공시는 `neutral`, **공시 0건이면 빈 배열 금지** → `neutral`/score 50 + "특이 공시 이력 없음" 1줄.
- **현재**: `qual.py`는 Hybrid RAG(RRF)+규칙으로 결정적 산출. 검색 품질은 [평가 보고서](eval_report.md) §RAG 참조.

## 5. Competitor (`prompts/competitor/system.md`)

- **역할**: `peer_tool`이 만든 구조화 JSON을 해석 → Strategist용 근거 카드.
- **출력 계약 (JSON)**: `peer_summary`(2~3문장), `evidence_cards[]`(`finding`·`metric_basis`·`confidence`∈{high,medium,low}·`flag`∈{strength,risk,neutral}), `bear_case`, `data_gaps[]`.
- **Anti-Hallucination(Block J)**: 입력에 없는 수치·기업·티커 생성 금지, 모르는 값은 `data_gaps`, 매수/매도 지시 금지, 1차원 단정 금지(낮은 PER ≠ 자동 저평가), **peer<3이면 confidence는 low/medium으로 제한**.
- **방향성 가이드**: PER·PBR·부채비율 낮을수록 우호(적자기업 제외), ROE·영업이익률·매출성장률 높을수록 우위. 결측은 `N/A` + `data_gaps`.

## 6. InvestmentAnalyst (`prompts/investment_analyst/system.md`)

- **역할**: 정량·정성·Peer·거시 결과 + 사용자 적합도 종합 → 최종 분석 신호.
- **출력 계약 (JSON)**:

| 키 | 값 범위 |
|---|---|
| `signal` | `BUY` \| `HOLD` \| `SELL` |
| `confidence` | 0–100 |
| `suitability` | 0–100 (포트폴리오 적합도) |
| `headline` | 한 문장 요약 |
| `key_reasons` | string[] (3) |
| `risks` | string[] (2) |
| `next_actions` | string[] (2) |

- **핵심 제약**: 수익 보장·무조건 매수/매도 등 확정 표현 금지, 입력에 없는 수치·뉴스·가격 생성 금지, **종목 매력도와 포트폴리오 적합도 분리**, 안정형은 고변동·고비중·단기급등에 보수적, 공격형도 손실감내·기간·현금필요 불일치 시 적합도 하향.
- **확장 필드**: LLM이 `executive_summary`/`investment_thesis`/`valuation`/`risk_analysis`/`action_plan` 반환 시 `InvestmentReport`로 매핑(`investment_analyst.py:102-119`).

---

## 7. 변경·회귀 규칙

- 프롬프트 변경 시 관련 단위 테스트 + `eval/run_benchmark.py`로 회귀 확인(`prompts/README.md`).
- 출력 키·enum 변경은 반드시 `schemas/`·Agent parser와 동시 갱신(계약 깨짐 방지).
- 본 명세는 `system.md` 변경 시 함께 갱신하며, 변경 영향은 [평가 보고서](eval_report.md)·[요약본](ai_summary_1pager.md)에 반영합니다.
