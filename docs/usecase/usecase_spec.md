# 유스케이스 정의서 (Use Case Specification)

> 기준 코드(SSOT): [`pipeline_11node_groundtruth.md`](../architecture/pipeline_11node_groundtruth.md) · 다이어그램 정본: [`canonical_diagrams.md`](../architecture/canonical_diagrams.md) §5
> 작성: PM 문서화 트랙 (2026-06-20, 코드 읽기 기반 · 코드 미수정)
> 근거 코드: `streamlit_app.py`(UI 흐름), `src/stock_agent/intake.py`(온보딩 7카드·종목 카탈로그), `src/stock_agent/schemas/analysis.py`(입출력 계약), `src/stock_agent/graph/pipeline.py`(11노드), `eval/golden_set/personas.json`(액터 검증 5케이스)

---

## 1. 목적과 범위

본 문서는 stock-agent가 **누가(액터) · 어떤 목적으로 · 어떤 흐름으로** 사용되는지를 정의한다. 강사 재검토 항목4가 "유스케이스 정의서 부재"로 캡 3을 부여한 항목을 해소하며, 모든 흐름은 실제 11노드 파이프라인(`pipeline.py`)과 입출력 계약(`schemas/analysis.py`)에 1:1로 매핑된다.

- **범위 내**: Streamlit 단일 사용자 분석 흐름(온보딩→포트폴리오→대화형 질의→Tier 1/2/3 결과→산출물), 골든셋 평가.
- **범위 외**: 회원 인증/결제, 실거래 주문(시스템 출력은 투자 권유가 아닌 분석 신호).

---

## 2. 액터 정의

### 2.1 주 액터 (Primary)

| 액터 | 설명 | 주요 목표 |
|---|---|---|
| **개인 투자자** | 반도체·금융 종목을 보유/관심하는 일반 투자자. 투자성향 7문항으로 프로파일링됨 | 보유 종목 검토·매수/매도 판단·포트폴리오 점검·근거 확인 |
| **평가 관리자** | 팀 평가 담당(PM/평가팀). 골든셋 5페르소나로 파이프라인 품질을 회귀 검증 | RAGAS·규칙 기반 평가 수치 확보 |

### 2.2 보조 액터 (Supporting · 외부 시스템)

| 액터 | 역할 | 연동 노드 | 실패 시 폴백 |
|---|---|---|---|
| **DART** | 재무·공시 원천 | Quant·Qual | mock / fallback evidence |
| **pykrx / KRX** | 시세·시장지표 | Quant·Competitor·Macro | mock |
| **뉴스 소스(네이버 등)** | 뉴스 RAG 원문 | Qual | fallback_news_docs |
| **ECOS** | 거시지표 | Macro | mock |
| **MCP peer 서버** | 실시간 peer 데이터 | Competitor | DB→**MCP**→mock 3단 중 2단 |
| **LLM (OpenRouter qwen / GLM)** | 분류·합성·최종 보정 | Classifier·Competitor·InvestmentAnalyst·Curator | rule-based / conservative fallback |

> 보조 액터의 실패가 전체 분석을 중단시키지 않는다(`_safe_worker_node` 격리, `pipeline.py:169-184`). "분석은 계속하되 신뢰도는 낮춘다"가 설계 원칙.

---

## 3. 유스케이스 목록

| ID | 유스케이스 | 주 액터 | intent (`RequestIntent`) | scope | 비고 |
|---|---|---|---|---|---|
| **UC-S1** | 투자성향 온보딩 & 프로필 생성 | 개인 투자자 | — | — | 온보딩 7카드 → `UserProfile` |
| **UC-S2** | 포트폴리오 입력 | 개인 투자자 | — | — | 텍스트 파싱/선택 → `Portfolio` |
| **UC-A1** | 보유 종목 검토 | 개인 투자자 | `holding_review` | single_stock | 대표 흐름(상세 기술) |
| **UC-A2** | 신규/추가 종목 추천 | 개인 투자자 | `new_recommendation` | single_stock/sector | Curator 후보 추천 |
| **UC-A3** | 리스크 점검 | 개인 투자자 | `risk_review` | single_stock | urgency=drop/news |
| **UC-A4** | 매도 판단 | 개인 투자자 | `sell_decision` | single_stock | urgency=drop |
| **UC-A5** | 포트폴리오 전반 점검 | 개인 투자자 | `portfolio_review` | portfolio | **macro 포함** |
| **UC-O1** | 산출물 다운로드 | 개인 투자자 | — | — | PDF·Excel·HTML |
| **UC-M1** | 골든셋 평가 | 평가 관리자 | (5종 전체) | — | `run_benchmark.py` + RAGAS |

다이어그램: [`canonical_diagrams.md`](../architecture/canonical_diagrams.md) §5 유스케이스 다이어그램.

---

## 4. 유스케이스 상세

### UC-A1. 보유 종목 검토 (대표 흐름)

| 항목 | 내용 |
|---|---|
| **주 액터** | 개인 투자자 |
| **목표** | 보유 종목을 계속 보유할지 데이터 기반으로 판단 |
| **사전조건** | UC-S1(프로필)·UC-S2(포트폴리오) 완료. `AgentState`에 `user_profile`·`portfolio` 존재 |
| **트리거** | "4. 대화형 질문"에 질의 입력 후 `분석 실행`(`streamlit_app.py:479-493`) |

**주 흐름 (Main Flow) — 11노드 매핑**
1. 투자자가 질의 입력 (예: "삼성전자 계속 가져가도 될까?")
2. **① Curator**: 질의·포트폴리오에서 대상 종목·섹터 확정 → `CuratorResult`
3. **② RequestClassifier**: intent=`holding_review`, scope=`single_stock`, depth 결정 + **worker_plan 산출** → `UserRequest`, `graph_route`
4. **③④⑤ (+⑥) 워커 fan-out**: Send API로 `quant·qual·competitor` 병렬 실행(섹터 확인 시 `macro` 포함, `pipeline.py:154-166`)
5. **⑦ Strategist**: 가용 워커 결과 가중 합성 → `StrategistResult(signal/confidence/suitability)`
6. **⑧ InvestmentAnalyst**: sLLM(qwen-2.5-7b)으로 최종 신호·문장 보정
7. **⑨ Guardrail**: 7게이트 위험표현·PII 검증
8. **⑩ Guardrail Apply**: 검증 결과 반영(필요 시 재생성 루프)
9. **⑪ ResultRenderer**: Tier 1(신호) / Tier 2(근거) / Tier 3(산출물) 렌더
10. UI가 노드별 진행을 점진 표시(`streamlit_app.py:425-448`) 후 결과 출력

**사후조건**: `AnalysisOutput(tier1, tier2, tier3, state)` 생성, 화면에 BUY/HOLD/SELL 신호와 근거 표시.

**대안 흐름 (Alternative)**
- **A1-1 요약 모드**: `requested_depth == "summary"`이면 Tier 2 근거를 항목당 1건으로 축약(`pipeline.py:558-561`).
- **A1-2 macro 포함**: scope가 portfolio/sector거나 single_stock+섹터 확인 시 macro 워커 추가 → UC-A5 흐름.
- **A1-3 추가 질의**: 동일 세션에서 대화형 질문 반복(재실행).

**예외 흐름 (Exception) — 실제 폴백 코드**
- **E1 워커 실패**: 한 워커 예외 → `_safe_worker_node`가 `worker_errors`에 격리, 나머지로 진행(`pipeline.py:169-184`).
- **E2 워커 다수 실패**: Strategist가 가용 워커만 재정규화, 전부 실패 시 conservative `HOLD`+`degraded=True`(`pipeline.py:225-258`).
- **E3 외부 데이터 실패**: Competitor DB→MCP→mock 3단 폴백(`competitor.py:310-325`), Qual fallback evidence + `fallback_reason`.
- **E4 LLM 실패**: InvestmentAnalyst가 기존 Strategist 결과로 fallback.
- **E5 민감정보(PII)**: Guardrail이 차단 → headline 마스킹·`HOLD`·confidence/suitability −30(`pipeline.py:303-330`).
- **E6 근거 부족/정합 결함**: Guardrail `needs_revision` → recomposer 재생성 루프 최대 2회(`pipeline.py:335-372`).

---

### UC-A2. 신규/추가 종목 추천

| 항목 | 내용 |
|---|---|
| **차이점** | intent=`new_recommendation`. Curator가 후보 종목(`candidates`)을 추천. scope single_stock 또는 sector |
| **주 흐름** | UC-A1과 동일한 11노드. Curator가 보유 외 후보 큐레이션, Competitor가 peer 비교로 상대 위치 제시 |
| **예외** | 카탈로그 외 종목 → Curator `warnings`, corp_code 미해소 시 보정 시도 |

### UC-A3. 리스크 점검

| 항목 | 내용 |
|---|---|
| **차이점** | intent=`risk_review`, urgency=`drop`/`news`/`earnings`. 리스크 항목·하방 시나리오 강조 |
| **주 흐름** | UC-A1 동일. Qual이 악재 evidence·event_types, Strategist `risks` 강조 |

### UC-A4. 매도 판단

| 항목 | 내용 |
|---|---|
| **차이점** | intent=`sell_decision`, urgency=`drop`. SELL/HOLD 변별 |
| **주 흐름** | UC-A1 동일. 손실 폭(`max_drawdown_tolerance`)·유동성 니즈와 대조해 매도 적합도 산출 |
| **사후조건** | Tier 1 신호가 SELL이면 disclaimer 강화(투자 권유 아님 고지) |

### UC-A5. 포트폴리오 전반 점검

| 항목 | 내용 |
|---|---|
| **차이점** | intent=`portfolio_review`, scope=`portfolio` → **macro 워커 항상 포함**(`worker_plan`에 4워커) |
| **주 흐름** | UC-A1 + ⑥ Macro 노드 실행. Strategist가 거시 가중(`_WEIGHTS_WITH_MACRO`) 소비 |
| **대안** | 다종목 포트폴리오 → 섹터 가중(`Portfolio.sector_weights`) 반영 |

---

### UC-S1. 투자성향 온보딩 & 프로필 생성

| 항목 | 내용 |
|---|---|
| **주 액터** | 개인 투자자 |
| **트리거** | 앱 진입 → 온보딩 카드 시작(`_render_onboarding_step`, `streamlit_app.py:114`) |
| **주 흐름** | 7개 카드 응답(목적·기간·손실감내·하락반응·유동성·경험·관심산업, `intake.py:183-250`) → `run_investor_profile_agent` → `UserProfile` |
| **대안** | `이전`/`처음부터` 버튼으로 단계 이동·초기화(`:145-161`) |
| **사후조건** | `UserProfile`(risk_tolerance·horizon·drawdown·liquidity·preferred_sectors) 세션 저장 |

### UC-S2. 포트폴리오 입력

| 항목 | 내용 |
|---|---|
| **트리거** | 프로필 확정 후 포트폴리오 단계(`_render_portfolio_step`, `:190`) |
| **주 흐름** | 종목 텍스트("삼성전자 10주") 파싱 또는 카탈로그 선택 → `Holding` 생성 → 비중 자동 계산(`build_holding_weights`) → `Portfolio` |
| **예외** | 해석 불가 입력·중복 종목 → `warnings` 반환(`intake.py:285-291`), 사용자 재입력 |
| **사후조건** | `Portfolio`(holdings·cash_weight) 세션 저장, `투자성향 확인`으로 분석 진입 |

### UC-O1. 산출물 다운로드

| 항목 | 내용 |
|---|---|
| **트리거** | 분석 결과 화면의 "산출물 다운로드"(`_render_download_artifacts`, `:741`) |
| **주 흐름** | Tier 3 산출물을 HTML / Excel / PDF로 생성·다운로드(`_build_html_report`·`_build_excel_report`·`_build_pdf_report`) |
| **사후조건** | 파일이 사용자 디바이스로 다운로드(DB 미저장, 데이터 저장 원칙 준수) |

### UC-M1. 골든셋 평가 (관리자)

| 항목 | 내용 |
|---|---|
| **주 액터** | 평가 관리자 |
| **트리거** | `python eval/run_benchmark.py [--with-contexts]` |
| **주 흐름** | `personas.json` 5케이스를 Phase 1 파이프라인에 투입 → 규칙 기반 + RAGAS(faithfulness·context_precision) 평가 → `eval/reports/`에 리포트 |
| **사후조건** | 날짜별 평가 리포트 산출(현 항목8 근거). context_recall은 `reference` 채워야 활성 |

---

## 5. 페르소나 ↔ 유스케이스 매핑 (골든셋 5케이스)

| 페르소나(`personas.json`) | 질의 | intent | scope | 매핑 UC | 기대 신호 경향 |
|---|---|---|---|---|---|
| 박민호 (40대 보수, 삼성전자 장기) | "삼성전자 계속 가져가도 될까?" | holding_review | single_stock | UC-A1 | HOLD 경향 |
| 김지연 (30대 공격, SK하이닉스) | "비중 늘려도 돼?" | holding_review/new | single_stock | UC-A1/A2 | BUY 가능 |
| 이서준 (20대 초보) | "포트폴리오에서 볼만한 종목" | portfolio_review | portfolio | UC-A5 | 추천+점검 |
| 최은서 (50대 보수, 급락) | "손절해야 해?" | sell_decision | single_stock | UC-A4 | SELL/HOLD 변별 |
| 정하나 (30대 중립, 공시) | "공시 이슈 확인해줘" | holding_review | single_stock | UC-A3 | 정보 제공 |

> 이 매핑은 평가 관리자가 UC-M1에서 각 유스케이스의 회귀를 검증하는 기준이 된다.

---

## 6. 정합 추적

- 본 문서의 모든 흐름은 11노드 SSOT를 기준으로 한다. 코드 변경 시 SSOT → 본 문서 → 시각자료(`시각자료_인덱스.html`) 순으로 동기화.
- 인터페이스(노드별 입출력 계약 상세)는 [`interface_spec.md`](../interface/interface_spec.md)(Phase 0-2 예정)에서 다룬다.
