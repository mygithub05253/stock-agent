# 모델 카드 (Model Card) — stock-agent

> 기준 코드: `src/stock_agent/config.py`, `src/stock_agent/agents/*.py`, `src/stock_agent/llm/*.py`
> 기준 SSOT: [`docs/architecture/pipeline_11node_groundtruth.md`](../architecture/pipeline_11node_groundtruth.md)
> 작성: PM 문서화 트랙 (2026-06-20, 코드 읽기 기반 · 코드 미수정)

본 문서는 stock-agent가 사용하는 LLM·임베딩 모델의 **선택 근거·역할·한계·비용·라이선스**를 코드 기준으로 정리한 모델 카드입니다. 모든 모델 ID와 호출 경로는 `config.py`와 각 Agent 구현에서 직접 추출했습니다.

---

## 1. 모델 인벤토리 (코드 확정)

| 모델 | 제공자 | config 키 | 기본값 | 용도 |
|------|--------|-----------|--------|------|
| **Qwen2.5-7B-Instruct** | OpenRouter | `openrouter_model` | `qwen/qwen-2.5-7b-instruct` | InvestmentAnalyst 1차 합성, Competitor narrative |
| **GLM-4.5-Flash** | Z.ai (`api.z.ai`) | `glm_model` | `glm-4.5-flash` | Curator·RequestClassifier 구조화, InvestmentAnalyst 폴백 |
| **BGE-M3** | 임베딩 (로컬/HF) | `embedding_model` | `bge-m3` (1024-dim) | 뉴스·공시 RAG 임베딩 (pgvector `vector(1024)`) |

> LangSmith tracing은 기본 비활성(`langsmith_tracing=False`). 환경변수 placeholder만 존재하며 실제 추적 모듈은 후속 작업입니다.

---

## 2. Agent ↔ 모델 매핑 (코드 검증)

| 노드 (11노드 SSOT) | LLM 사용 | 모델 | 폴백 | 근거 코드 |
|---|---|---|---|---|
| 1. Curator | ✅ | GLM-4.5-flash | rule 기반 선택 | `agents/curator.py:71` |
| 2. RequestClassifier | ✅ | GLM-4.5-flash | rule 기반 분류 | `agents/request_classifier.py:93` |
| 3. Quant | ❌ | — (결정적 Python) | — | `agents/quant.py` (LLM 호출 없음) |
| 4. Qual | ❌ | — (결정적 + RAG) | — | `agents/qual.py` (LLM 호출 없음) |
| 5. Competitor | ✅ (narrative만) | Qwen-2.5-7b | narrative 생략(엔진은 결정적) | `agents/competitor.py:76,92` |
| 6. Macro | ❌ | — (결정적 Python) | — | `agents/macro.py` |
| 7. Strategist | ❌ | — (결정적 가중 합성) | conservative HOLD | `graph/pipeline.py:225` |
| 8. InvestmentAnalyst | ✅ | **Qwen-2.5-7b → GLM-4.5-flash → rule** (3단) | 아래 §3 | `agents/investment_analyst.py:86,124,135` |
| 9~10. Guardrail / Apply | ❌ | — (결정적 7게이트) | — | `graph/pipeline.py:266,293` |
| 11. Renderer | ❌ | — (템플릿 렌더) | — | `graph/pipeline.py:380` |

**핵심 사실 2가지 (드리프트 주의)**

1. **Quant·Qual은 현재 LLM 미연결**입니다. `prompts/quant/system.md`·`prompts/qual/system.md`는 향후 LLM 연결을 위한 **계약(명세)**으로 보관 중이며, 실제 분석은 도구·규칙 기반으로 산출합니다. ([프롬프트 명세서](prompt_spec.md) 참조)
2. **InvestmentAnalyst의 1차 모델은 GLM이 아니라 Qwen(OpenRouter)**입니다. README 구문상 "GLM으로 최종 분석"은 폴백 경로 표현이며, 코드상 우선순위는 Qwen → GLM → local-rule입니다.

---

## 3. InvestmentAnalyst 3단 LLM 라우팅 (`investment_analyst.py:79-172`)

```
openrouter_api_key 있음? ──예──▶ Qwen-2.5-7b 호출 (max_tokens=900)
        │아니오/실패                       │성공 → 반환 (fallback_used=False)
        ▼                                   │실패 → llm_errors 누적 ↓
glm_api_key 있음? ─────예──▶ GLM-4.5-flash 호출
        │아니오                              │성공 → 반환 (fallback_used=True)
        ▼                                   │실패 ↓
local-rule strategist 결과 유지 (fallback_used=True, model=local-rule)
```

- **비용 라우팅 의도**: 무료/저가 sLLM(Qwen-7b)을 1차로 두고, 장애 시에만 GLM으로 승계, 그조차 실패하면 결정적 결과를 보존 → **키 없이도 화면이 뜬다**(데모 안정성).
- 모든 경로에서 `model_provider`·`model`·`fallback_used` 메타데이터를 `strategist` 결과에 기록 → 평가·관측 가능.

---

## 4. 선택 근거 (Why these models)

| 결정 | 근거 |
|------|------|
| **sLLM(Qwen-7b) 우선** | 부트캠프 비용 정책(월 5만원 캡, PRD Non-goal)에 맞춘 저비용 1차 합성. 구조화 JSON 출력에 7B급으로 충분. |
| **GLM-4.5-flash 폴백** | OpenRouter 장애·레이트리밋 대비 이종 제공자 이중화. flash 등급으로 저지연·저비용. |
| **결정적 Strategist/Guardrail** | 금융 신호의 재현성·감사가능성 확보. 위험 표현 차단은 LLM 확률에 맡기지 않고 규칙 게이트로 강제. |
| **BGE-M3 1024-dim** | 한국어 포함 다국어 성능과 pgvector 호환(고정 차원). Hybrid(RRF) 검색의 dense 측 담당. |

---

## 5. 한계와 위험 (Limitations)

- **RAG faithfulness 목표 미달**: 2026-06-12 벤치마크 faithfulness **0.4096 / 목표 0.80**. 생성 문장이 검색 근거를 충분히 반영하지 못하는 구간 존재 → [평가 보고서](eval_report.md) 개선 대상.
- **소형 모델 환각 위험**: 7B sLLM은 수치·사실 환각 가능. 이를 **프롬프트 anti-hallucination 제약 + 결정적 도구 계산 분리 + Guardrail 게이트** 3중으로 억제(자세한 계약은 [프롬프트 명세서](prompt_spec.md)).
- **단일 종목 mock 구간**: 일부 worker는 MVP mock 데이터 기반(README 빠른 시작 주의 참조). 실데이터 연결은 단계적.
- **비용 상한**: 월 5만원 캡. Self-Consistency는 N=3로 축소 운영([LLM 비용 가이드](../operations/llm_cost_guide.md)).

---

## 6. 비용·운영

| 항목 | 값 / 정책 |
|------|-----------|
| 월 비용 상한 | **5만원 초과 금지** (PRD Non-goal) |
| 타임아웃 | OpenRouter 30s, GLM 30s, Competitor MCP 20s (`config.py`) |
| 재시도 | OpenRouter 클라이언트 재시도 내장 (`llm/openrouter_client.py`) |
| 캐싱 | 동일 종목 24h 내 재분석 시 DB 캐시 (비용 가이드) |
| 키 부재 시 | 전 경로 rule/mock 폴백 → 데모 가능 |

---

## 7. 라이선스·데이터 취급

- **Qwen2.5-7B-Instruct**: Apache-2.0 (Qwen 라이선스). OpenRouter 경유 API 호출.
- **GLM-4.5-Flash**: Z.ai 상용 API 약관 적용.
- **BGE-M3**: MIT 라이선스(BAAI).
- **PII**: Guardrail Apply 단계에서 민감정보 감지 시 headline 마스킹 + `signal=HOLD` 강등(`pipeline.py:303-330`). API 키·`.env`는 커밋 금지(README 협업 가이드 §6).

---

> 본 모델 카드는 코드(`config.py`·agents·llm) 변경 시 함께 갱신합니다. 모델 ID·라우팅이 바뀌면 이 문서를 먼저 고치고 [요약본](ai_summary_1pager.md)을 따라 갱신하세요.
