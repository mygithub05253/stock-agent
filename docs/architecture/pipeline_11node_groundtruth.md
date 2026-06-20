# 11노드 파이프라인 그라운드 트루스 (코드 확정 SSOT)

> **이 문서는 `src/stock_agent/graph/pipeline.py`에서 직접 추출한 단일 기준점(Single Source of Truth)입니다.**
> 모든 설계 문서(아키텍처·시퀀스·유스케이스·인터페이스·ERD·README)는 이 표를 기준으로 정합을 맞춥니다.
> 코드가 바뀌면 **이 문서를 먼저 갱신**한 뒤 파생 문서를 따라 고칩니다.

- 기준 커밋 기준 파일: `src/stock_agent/graph/pipeline.py`
- 그래프 빌더: `build_analysis_graph()` (`pipeline.py:388-437`)
- 작성: PM 문서화 (2026-06-20, 코드 읽기 기반 · 코드 미수정)

---

## 1. 노드 인벤토리 (11개)

| # | 노드(코드명) | UI 라벨 | 책임 | 주요 입력 | 주요 출력 | 구현 함수 |
|---|---|---|---|---|---|---|
| 1 | `curator` | Curator | 사용자 질의·포트폴리오에서 분석 대상 종목/섹터 큐레이션 | `user_query`, `portfolio` | `curator: CuratorResult` | `_curator_node` (`:132`) |
| 2 | `classifier` | RequestClassifier | intent·scope·urgency·depth 분류 + **worker_plan 결정** | `user_query`, `curator` | `user_request`, `graph_route` | `_classifier_node` (`:137`) |
| 3 | `quant` | Quant | DART 재무 + pykrx 시세 정량 분석 | `curator`, `portfolio` | `quant: QuantResult` | `_quant_node` (`:204`) |
| 4 | `qual` | Qual | 뉴스·공시 Hybrid RAG 정성 분석 | `curator` | `qual: QualResult` | `_qual_node` (`:208`) |
| 5 | `competitor` | Competitor | 동종 Peer 추출·횡비교 (DB→MCP→mock 3단 폴백) | `curator` | `competitor: CompetitorResult` | `_competitor_node` (`:212`) |
| 6 | `macro` | Macro | 거시경제 환경 분석 (**조건부 실행**) | `curator` | `macro: MacroResult` | `_macro_node` (`:216`) |
| 7 | `strategist` | Strategist | 실행된 워커 결과 join·가중 합성 → 분석 신호 | 워커 결과 전체 | `strategist: StrategistResult` | `_strategist_node` (`:225`) |
| 8 | `investment_analyst` | InvestmentAnalyst | sLLM(qwen-2.5-7b)으로 최종 신호·적합도 보정 | `strategist` | `strategist`(갱신) | `_investment_analyst_node` (`:261`) |
| 9 | `guardrail` | Guardrail | 7게이트 위험표현·PII 검증 (`passed = not blocked`) | `strategist` | `guardrail: GuardrailResult` | `_guardrail_node` (`:266`) |
| 10 | `guardrail_apply` | Guardrail Apply | PII 차단 폴백 + **recomposer revision loop(≤2)** | `strategist`, `guardrail` | `strategist`, `guardrail`(갱신) | `_apply_guardrail_node` (`:293`) |
| 11 | `renderer` | ResultRenderer | Tier 1/2/3 결과 렌더링 | 전체 state | `rendered_report` | `_renderer_node` (`:380`) |

> 비고: 직전 문서들의 "6 에이전트"/"9 에이전트" 표기는 모두 폐기. 그래프에 실제 등록된 노드는 **11개**(`pipeline.py:404-414`).

---

## 2. 엣지·흐름 (확정)

```
START
  └→ curator → classifier
                   └─(_fanout_workers, Send API)→ [ quant | qual | competitor | (macro) ]   ← 동적 병렬 fan-out
                                                          └────────── join ──────────┘
                                                                       ↓
                                                                  strategist
                                                                       ↓
                                                              investment_analyst
                                                                       ↓
                                                                   guardrail
                                                                       ↓
                                                               guardrail_apply ──(revision loop ≤2)
                                                                       ↓
                                                                    renderer → END
```

- `START → curator`: `pipeline.py:417`
- `curator → classifier`: `:418`
- `classifier → _fanout_workers` (조건부 Send): `:423`
- `quant/qual/competitor/macro → strategist` (join): `:426-429`
- `strategist → investment_analyst → guardrail → guardrail_apply → renderer → END`: `:431-435`

---

## 3. 핵심 분기 로직 2종 (문서·다이어그램에 반드시 반영)

### 3.1 worker_plan — macro 조건부 실행 (`_worker_plan`, `pipeline.py:154-166`)

- 기본 워커: `quant`, `qual`, `competitor` (항상 실행)
- `macro` 추가 조건:
  - `analysis_scope ∈ {portfolio, sector}`, **또는**
  - `analysis_scope == single_stock` **이면서** `curator.sector`가 확인된 경우
- 근거(코드 주석): "개별 종목도 업종 거시경제 환경에 직접 영향받음"
- 효과: macro가 plan에 없으면 **Send 자체를 안 보냄** → 노드 실행 0회 (스킵 로직 불필요)

### 3.2 revision loop — guardrail_apply 내부 재생성 (`_apply_guardrail_node`, `pipeline.py:335-372`)

- 트리거: `guardrail.needs_revision == True` 또는 `passed == False`
- 루프(최대 `max_retries = 2`): `recomposer → strategist → investment_analyst → guardrail` 재호출
- PII 차단 경로(`:303-330`): 민감정보 감지 시 headline 마스킹 + `signal=HOLD` + confidence/suitability −30 강등
- 예외 처리: 루프 실패 시 `worker_errors`에 누적, 파이프라인은 계속 진행

---

## 4. 에러핸들링·폴백 (코드 확정)

| 노드 | 폴백/격리 | 코드 |
|---|---|---|
| 워커 4종 | `_safe_worker_node` try/except → `worker_errors` 누적, 한 노드 실패가 전체로 전파 안 됨 | `:169-184` |
| strategist | 예외 시 conservative fallback(`HOLD`, `degraded=True`, `fallback_used=True`) | `:225-258` |
| strategist | 워커 일부 실패 시 `degraded=True` + 실패 노드 risk 누적 | `:248-257` |
| guardrail | 예외 시 `passed=False` + `risk_level=high` 반환 | `:270-290` |
| renderer | 예외 시 `worker_errors` 누적 | `:384-385` |

---

## 5. 파생 문서 정합 체크리스트

이 SSOT 기준으로 다음 문서를 교정해야 함(드리프트 해소):

- [ ] `docs/architecture/multi_agent_architecture.md` — 6에이전트 → 11노드 컴포넌트도
- [ ] `docs/architecture/system_flow.md` — 시퀀스도 11노드로
- [ ] `docs/architecture/agent_design.md` — 노드별 상세 11개로
- [ ] `docs/decisions/ADR-003-six-agent-structure.md` — 11노드 전환 ADR 추가 또는 supersede
- [ ] `README.md` — "주요 에이전트 9개" → 11노드 정합 + Mermaid 갱신
- [ ] `docs/architecture/erd.md` — 별건(ERD 정합)

> 갱신 시 각 문서 상단에 `> 기준: docs/architecture/pipeline_11node_groundtruth.md` 를 명시해 추적성을 남긴다.
