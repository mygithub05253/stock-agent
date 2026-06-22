# 요구사항 정의서 (SRS) — stock-agent

> 상위 문서: [`docs/prd/PRD_v0.6.md`](../prd/PRD_v0.6.md) (WHAT/WHY) — 본 SRS는 PRD를 **추적 가능한 요구사항 ID**로 승격합니다.
> 구현 정합 SSOT: [`docs/functional-spec/IMPLEMENTATION_STATUS.md`](../functional-spec/IMPLEMENTATION_STATUS.md)
> 11노드 SSOT: [`docs/architecture/pipeline_11node_groundtruth.md`](../architecture/pipeline_11node_groundtruth.md)
> 작성: PM 문서화 트랙 (2026-06-22, PRD·코드 기준)

## 0. 목적·범위

개인투자자가 **내 포트폴리오 컨텍스트에서 왜 그런 결정인지** 근거와 함께 받는 멀티에이전트 분석 시스템의 기능(FR)·비기능(NFR) 요구사항을 정의한다. 범위는 PRD §4(반도체·금융·소비재 9종목, 12주 MVP)를 따른다.

- 요구사항 우선순위: **M**(Must, Phase 1) / **S**(Should, Phase 2) / **C**(Could, v2).
- 상태는 구현 정합 매트릭스 기준: ✅ 구현 / 🟡 부분 / ⚠ 설계안 / ❌ 미구현.

---

## 1. 기능 요구사항 (FR)

### 1.1 내부/데이터 기능 (INT)

| ID | 요구사항 | 우선 | 상태 | 근거 |
|----|---------|:----:|:----:|------|
| FR-INT-1 | 뉴스 크롤링·정제 후 RAG 적재 | M | ✅ | `datas/news/`, 뉴스 RAG 임베딩 파이프라인(#74) |
| FR-INT-2 | DART 재무·공시, pykrx 시세 수집 | M | 🟡 | `tools/`, 일부 mock 폴백 |
| FR-INT-3 | pgvector 벡터 인덱싱·Hybrid(RRF) 검색 | M | ✅ | `rag/`, hit@5 1.0([평가](../ai/eval_report.md)) |
| FR-INT-4 | 거시지표(ECOS) 수집·적재 | S | ✅ | macro 759건 적재(#66) |

### 1.2 기본 기능 (FR-B, Phase 1) — PRD User Story 1~5

| ID | 요구사항 (As a … I want … so that) | 우선 | 상태 | 근거 (US / 코드) |
|----|---------|:----:|:----:|------|
| FR-B1 | 이메일·비번 가입 + 투자성향·관심섹터 등록 | M | 🟡 | US1 / 온보딩→`UserProfile` 동작, `users` DDL 미구현 |
| FR-B2 | 보유 종목·매수가·수량 일괄 입력 | M | 🟡 | US2 / `test_streamlit_intake.py`, `holdings` DDL 미구현(세션 보관) |
| FR-B3 | "삼성전자"/"005930" 검색·자동완성 | M | 🟡 | US3 / Curator corp_code 보정, 전체 universe UI 부분 |
| FR-B4 | 종목 1년 차트·PER/PBR·최근 7일 뉴스 요약 | M | 🟡 | US4 / `company`·`stock_price` 경로 존재, 일부 mock |
| FR-B5 | 포트폴리오 평가손익·비중·섹터분포 일괄 안내 | M | 🟡 | US5 / Strategist 종합·부분실패 허용(#51) |

### 1.3 고급 기능 (FR-A, Phase 2) — PRD User Story 6~11

| ID | 요구사항 | 우선 | 상태 | 근거 (US / 코드) |
|----|---------|:----:|:----:|------|
| FR-A1 | 보수/기본/낙관 3시나리오 5개년 적정주가 | S | 🟡 | US6 / Quant 계산·fallback(#53), MVP 3개년 |
| FR-A2 | 호재·악재 뉴스 출처 부착 정성 분석 | S | 🟡 | US7 / Qual RAG 폴백(#52), Reranker 미고도화 |
| FR-A3 | 동종 국내 ≥3개 Peer 횡비교(PER·ROE·성장) | S | ✅ **(100%)** | US8 / 3단 폴백·복합 유사도(#62)·이상치 플래깅·회귀 골든셋·MCP 외부노출 |
| FR-A4 | BUY/HOLD/SELL 한 줄 결론 + 4근거(WHAT·HOW MUCH·WHY·RISK) | S | 🟡 | US9 / 신호+Guardrail 게이팅(#50), HOLD 변별력 과제 |
| FR-A5 | 성향 맞춤 5~10개 후보 추천(3섹터) | S | 🟡 | US10 / Curator 후보 반환, 랭킹 고도화 부분 |
| FR-A6 | 7페이지 PB 리포트 PDF·DOCX 다운로드 | C | ⚠ | US11 / 산출 파일 경로 미구현 |

### 1.4 횡단 가드레일 (FR-G)

| ID | 요구사항 | 우선 | 상태 | 근거 |
|----|---------|:----:|:----:|------|
| FR-G1 | PII 마스킹 + 민감정보 시 HOLD 강등 | M | ✅ | `pipeline.py:303-330` |
| FR-G2 | 투자권유·확정표현 차단(7게이트) | M | ✅ | 7게이트 `passed=not blocked`(#50) |
| FR-G3 | 책임 고지 자동 부착 | M | ✅ | renderer / harness |
| FR-G4 | 근거 부족·위험 표현 시 재합성(revision ≤2) | M | ✅ | `_apply_guardrail_node`(#51) |

> 추적성: 각 FR은 PRD User Story 및 [기능 명세](../functional-spec/) B1~B5·A1~A6·D1과 1:1 대응. 구현 상태의 단일 출처는 [IMPLEMENTATION_STATUS](../functional-spec/IMPLEMENTATION_STATUS.md).

---

## 2. 비기능 요구사항 (NFR)

### 2.1 성능 (Performance)

| ID | 요구사항 | 목표 | 출처 |
|----|---------|------|------|
| NFR-P1 | Tier 1 응답시간 (캐시 모드) | ≤ 5초 | PRD §2.2 |
| NFR-P2 | Tier 1 응답시간 (LIVE 모드) | ≤ 60초 | PRD §2.2, Goal |
| NFR-P3 | Hello E2E 통과 종목 수 | ≥ 5종 | PRD §2.2 |

### 2.2 품질·신뢰성 (Quality)

| ID | 요구사항 | 목표 | 현재 | 출처 |
|----|---------|------|------|------|
| NFR-Q1 | RAGAS Faithfulness | ≥ 0.80 | **0.41** ⚠️ | PRD §2.3 / [평가](../ai/eval_report.md) |
| NFR-Q2 | Action Consistency (5회 반복 일치) | ≥ 80% | 미측정 | PRD §2.3 |
| NFR-Q3 | Tier1↔Tier3 결론 정합성 | ≥ 90% | 미측정 | PRD §2.3 |
| NFR-Q4 | 출처 부착률 | ≥ 95% | 미측정 | PRD §2.2 |
| NFR-Q5 | Guardrail 차단 정확도 | 100% | 골든셋 통과 | PRD §2.3 |

### 2.3 비용 (Cost) — 명시 상한

| ID | 요구사항 | 정책 | 상태 |
|----|---------|------|------|
| NFR-C1 | 월 LLM 운영비 | **≤ 5만원** (초과 금지) | 키 부재 시 LLM 생략만 구현, 단계 제어 ❌ |
| NFR-C2 | 4만원 도달 시 | 신규 분석 캐시 모드 강제 + 관리자 알림 | ⚠ 설계안 (PRD E5) |
| NFR-C3 | 5만원 도달 시 | 신규 분석 차단 | ⚠ 설계안 (PRD E5) |
| NFR-C4 | 모델 라우팅 | sLLM 우선 → 큰 모델은 복잡 결정만 | ✅ Qwen→GLM→rule([모델카드](../ai/model_card.md)) |

### 2.4 폴백·가용성 (Resilience / SLA)

| ID | 요구사항 | 동작 | 상태 |
|----|---------|------|------|
| NFR-R1 | LLM 타임아웃(>30초) | 재시도 후 실패 시 캐시/보수적 결과 | ✅ OpenRouter 재시도, 3단 폴백 |
| NFR-R2 | LLM 스키마 위반 | 1회 재시도 후 해당 노드만 결과 비움, 부분 출력 | ✅ 워커 격리 `_safe_worker_node` |
| NFR-R3 | 워커 일부 실패 | `degraded=True`로 계속 진행 | ✅ Strategist 부분실패 허용(#51) |
| NFR-R4 | Competitor DB 미연결 | MCP 실시간 시세→mock 3단 폴백 | ✅ |

### 2.5 보안·컴플라이언스 (Security / PII)

| ID | 요구사항 | 정책 | 상태 |
|----|---------|------|------|
| NFR-S1 | PII 감지·마스킹 | 민감정보 시 headline 마스킹 + HOLD 강등 | ✅ FR-G1 |
| NFR-S2 | 비밀키 관리 | `.env`·API키 커밋 금지, 프로세스 env 주입 | ✅ 협업가이드 §6 |
| NFR-S3 | 책임 고지 | "투자 권유 아님" 100% 부착 | ✅ FR-G3 |
| NFR-S4 | 데이터 한정 | 한국 KOSPI/KOSDAQ, 3섹터 | ✅ PRD §4 |

### 2.6 제약 (Constraints / Non-functional limits)

| ID | 제약 | 근거 |
|----|------|------|
| NFR-X1 | 동시 사용자 ≤ 3명 (Streamlit Cloud 무료 티어) | PRD Non-goal |
| NFR-X2 | WebSocket·푸시 미지원(클라이언트 폴링) | PRD Non-goal |
| NFR-X3 | 일봉 OHLCV만(실시간 분/초 시세 제외) | PRD Non-goal |
| NFR-X4 | 자동매매·주문집행 절대 미구현 | PRD Non-goal (규제) |

---

## 3. 예외/엣지 케이스 요구사항 (PRD §7 매핑)

| ID | 상황 | 처리 | PRD |
|----|------|------|-----|
| FR-E1 | 5y 재무 미확보·공시 없음 | "데이터 부족" 안내 + 가용/부족 연도 명시 | E1 |
| FR-E2 | 24h 내 ±10% 급변동 | 결과 보류 + 재분석 권장 | E2 |
| FR-E3 | 비중 합 ≠ 100% | 자동 정규화 + 경고 | E3 |
| FR-E4 | MVP 섹터 외 종목 | "정확도 보장 안 됨" 경고 | E3 |
| FR-E5 | BUY인데 신뢰도<60% 또는 적합도 최저 | HOLD 다운그레이드 강제 | E6 |

---

## 4. 추적성 매트릭스 (요약)

| 요구사항 | PRD | 기능명세 | 코드/테스트 | 평가 |
|---------|-----|---------|------------|------|
| FR-A3 (Peer) | US8 | A3 | `agents/competitor.py`, `tests/tools/test_peer_tool.py`(17) | Competitor 6/6 |
| FR-G1~G4 (Guardrail) | §4 가드레일 | — | `tests/agents/test_guardrail_agent.py`(9) | 차단 100% |
| FR-A2 (정성) | US7 | A2 | `rag/`, `tests/rag/`(8) | RAG hit@5 1.0, faithfulness 0.41 |
| NFR-Q1 | §2.3 | — | `eval/run_benchmark.py` | 0.41/0.80 |

> 본 SRS는 PRD·코드 변경 시 함께 갱신한다. 시험 시나리오는 [테스트 명세서](../testing/test_spec.md), 달성 현황 서사는 [결과 보고서](../report/result_report.md) 참조.
