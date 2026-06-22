# 테스트 명세서 / 계획서 (Test Specification) — stock-agent

> 기준 코드: `tests/` (전 디렉토리), `eval/` 평가 하네스
> 정합 SSOT: [`docs/functional-spec/IMPLEMENTATION_STATUS.md`](../functional-spec/IMPLEMENTATION_STATUS.md), [SRS](../requirements/srs.md)
> 작성: PM 문서화 트랙 (2026-06-22, 테스트 코드 직접 집계 · 코드 미수정)

## 0. 개요

- 총 테스트 함수: **137개** (`tests/`, pytest 기준).
- 게이트: CI(`.github/workflows/ci.yml`)에서 `compileall + pytest + 충돌마커 검출(#63)`로 PR 자동 검증.
- 평가 하네스: `eval/run_benchmark.py`(rule+RAGAS), `eval/run_competitor_eval.py`(순수 엔진, 비용 0) — 결과는 [평가 보고서](../ai/eval_report.md).

## 1. 테스트 인벤토리 (코드 집계)

| 영역 | 파일 | 함수 수 | 대상 (SRS) |
|------|------|:---:|------|
| 파이프라인 E2E | `tests/test_phase1_pipeline.py` | 29 | 11노드 흐름·폴백·revision |
| Peer 엔진 | `tests/tools/test_peer_tool.py` | 17 | FR-A3 |
| OpenRouter 클라이언트 | `tests/llm/test_openrouter_client.py` | 11 | NFR-R1, 모델 호출 |
| MCP 브리지 | `tests/mcp_bridge/test_mcp_bridge.py` | 11 | FR-A3 MCP 폴백 |
| Guardrail | `tests/agents/test_guardrail_agent.py` | 9 | FR-G1~G4 |
| Competitor LLM narrative | `tests/agents/test_competitor_llm.py` | 8 | FR-A3 |
| Competitor Agent | `tests/agents/test_competitor_agent.py` | 6 | FR-A3 |
| Quant Agent | `tests/agents/test_quant_agent.py` | 5 | FR-A1 |
| Macro Agent | `tests/agents/test_macro_agent.py` | 5 | FR-INT-4, macro 분기 |
| Retriever | `tests/rag/test_retriever.py` | 4 | FR-INT-3, FR-A2 |
| Strategist | `tests/agents/test_strategist_agent.py` | 4 | FR-B5, FR-A4 |
| MCP 핸드셰이크 | `tests/mcp_bridge/test_mcp_handshake.py` | 4 | FR-A3 A2A |
| Competitor eval | `tests/test_competitor_eval.py` | 4 | 회귀 |
| 평가 하네스 | `tests/test_eval_harness.py` | 4 | NFR-Q1 |
| Qual Agent | `tests/agents/test_qual_agent.py` | 3 | FR-A2 |
| Competitor schema | `tests/test_competitor_schema.py` | 3 | 계약 |
| 파이프라인↔Guardrail 통합 | `tests/agents/test_pipeline_guardrail_integration.py` | 2 | FR-G |
| 뉴스 임베딩 | `tests/rag/test_news_embedding_pipeline.py` | 2 | FR-INT-1 |
| RAG retriever eval | `tests/rag/test_rag_retriever_eval.py` | 2 | FR-INT-3 |
| Streamlit intake | `tests/test_streamlit_intake.py` | 2 | FR-B1, FR-B2 |
| Recomposer | `tests/test_recomposer.py` | 1 | FR-G4 revision |
| Result renderer | `tests/test_result_renderer.py` | 1 | FR-B4 렌더 |
| **합계** | | **137** | |

## 2. 주요 테스트 시나리오 (대표)

### 2.1 파이프라인 E2E (`test_phase1_pipeline.py`, 29)
- 11노드 흐름: curator→classifier→(fan-out)→strategist→analyst→guardrail→apply→renderer.
- macro 조건부 실행: `analysis_scope`/`sector`에 따른 Send 발송 여부.
- 부분 실패: 워커 1개 예외 시 `degraded=True`로 계속 진행(FR/NFR-R3).
- revision loop: guardrail `needs_revision` 시 재합성(≤2)(FR-G4).

### 2.2 Competitor / Peer (총 38: 6+8+17+3+4)
- 3단 폴백(DB→MCP 실시간→mock), 복합 유사도 정렬(#62), 시총 band 거름, 이상치(outlier) 플래깅, peer<3 confidence 제한.
- 회귀 골든셋 C1~C6 ↔ [평가 보고서](../ai/eval_report.md) §3.

### 2.3 Guardrail (9 + 통합 2)
- 7게이트 차단(`passed=not blocked`), PII 마스킹·HOLD 강등(FR-G1), 위험표현 차단(FR-G2), 책임고지 부착(FR-G3).

### 2.4 RAG (8)
- Hybrid RRF 검색 hit@5/MRR/nDCG, 뉴스 임베딩 파이프라인 적재·차원(1024) 검증(FR-INT-1/3).

### 2.5 LLM 클라이언트·폴백 (11)
- OpenRouter 재시도·타임아웃·에러 처리(NFR-R1), 스키마 위반 처리(NFR-R2).

## 3. 평가(품질) 테스트 — 하네스

| 평가 | 스크립트 | 측정 | 목표 | 현재 |
|------|---------|------|------|------|
| 파이프라인 rule-based | `eval/run_benchmark.py` | 출력 계약 통과 | — | 40/41 |
| RAGAS | `eval/run_benchmark.py` | faithfulness | ≥0.80 | 0.41 ⚠️ |
| Competitor 회귀 | `eval/run_competitor_eval.py` | 6케이스 | 6/6 | 6/6 |
| RAG 검색 | `tests/rag/test_rag_retriever_eval.py` | hit/MRR/nDCG | — | 1.0/1.0/0.93 |

## 4. 테스트 계획 (미충족·확장)

| 우선 | 항목 | 근거 (SRS) |
|:---:|------|------|
| 🔴 | RAGAS faithfulness 0.41→0.80 회귀 추가 | NFR-Q1 |
| 🟠 | Action Consistency 5회 반복 일치율 측정 | NFR-Q2 |
| 🟠 | Tier1↔Tier3 정합성 자동 비교 | NFR-Q3 |
| 🟡 | 출처 부착률 자동 측정 | NFR-Q4 |
| 🟡 | 응답시간(캐시/LIVE) 측정 자동화 | NFR-P1/P2 |
| 🟢 | 영속화(users/holdings) 테스트 (DDL 구현 후) | FR-B1/B2 |

## 5. 실행 방법

```bash
pip install -r requirements-dev.txt
pytest                       # 전체 137개
pytest tests/agents -q       # 영역별
python eval/run_benchmark.py        # rule + RAGAS
python eval/run_competitor_eval.py  # Competitor 회귀(비용 0)
```

> 본 명세는 `tests/` 변경 시 함께 갱신한다. 달성 현황 서사는 [결과 보고서](../report/result_report.md) 참조.
