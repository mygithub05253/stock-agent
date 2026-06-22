# 정본 다이어그램 (Canonical Mermaid)

> **모든 시각자료·README·설계문서가 복붙해 쓰는 단일 정본 Mermaid입니다.**
> 기준점: [`pipeline_11node_groundtruth.md`](pipeline_11node_groundtruth.md) (= `src/stock_agent/graph/pipeline.py:404-435`).
> GitHub·Obsidian·VS Code에서 그대로 렌더됩니다. PNG가 필요하면 이 코드를 이미지 변환만 하면 됩니다(내용은 이미 확정).
> 코드가 바뀌면 **이 파일을 먼저 고치고**, 각 HTML은 [`시각자료_인덱스.html`](../시각자료_인덱스.html)의 수정 포인트를 Codex에 지시해 동기화합니다.

---

## 1. 마스터 파이프라인 플로우차트 (11노드)

```mermaid
flowchart TD
    START([START]) --> CUR["①  Curator<br/>의도 파악·종목/섹터 큐레이션"]
    CUR --> CLS["②  RequestClassifier<br/>intent·scope·depth 분류<br/>+ worker_plan 결정"]

    CLS -. "_fanout_workers · Send API" .-> FAN{{"동적 fan-out<br/>worker_plan 기반 병렬"}}

    subgraph WORKERS["병렬 워커 (실행된 노드만 join)"]
      direction LR
      QNT["③  Quant<br/>재무·시세 정량"]
      QAL["④  Qual<br/>뉴스·공시 Hybrid RAG"]
      CMP["⑤  Competitor<br/>Peer 횡비교<br/>DB→MCP→mock 3단 폴백"]
      MAC["⑥  Macro<br/>거시경제 · 조건부"]
    end

    FAN --> QNT
    FAN --> QAL
    FAN --> CMP
    FAN -. "scope∈{portfolio,sector}<br/>또는 single_stock+섹터확인" .-> MAC

    QNT --> STR
    QAL --> STR
    CMP --> STR
    MAC --> STR

    STR["⑦  Strategist<br/>워커 join·가중 합성<br/>(가용 워커 재정규화)"] --> INV["⑧  InvestmentAnalyst<br/>sLLM(qwen-2.5-7b) 신호 보정"]
    INV --> GRD["⑨  Guardrail<br/>7게이트 검증 (passed = not blocked)"]
    GRD --> GAP["⑩  Guardrail Apply<br/>PII 차단 + revision loop"]

    GAP -. "needs_revision 또는 !passed (≤2회)" .-> RECOMP[["recomposer → strategist<br/>→ investment_analyst → guardrail"]]
    RECOMP -.-> GAP

    GAP --> RND["⑪  ResultRenderer<br/>Tier 1/2/3 렌더"]
    RND --> ENDN([END])

    classDef entry fill:#0f172a,color:#fff,stroke:#0f172a;
    classDef core fill:#eff6ff,color:#1e3a8a,stroke:#2563eb;
    classDef worker fill:#ecfdf5,color:#065f46,stroke:#059669;
    classDef guard fill:#fffbeb,color:#92400e,stroke:#d97706;
    classDef loop fill:#fef2f2,color:#991b1b,stroke:#dc2626,stroke-dasharray:4 3;

    class START,ENDN entry;
    class CUR,CLS,STR,INV,RND core;
    class QNT,QAL,CMP,MAC worker;
    class GRD,GAP guard;
    class RECOMP loop;
```

**읽는 법:** 실선 = 항상 실행, 점선 = 조건부. `Macro`는 worker_plan에 포함될 때만 Send가 발송돼 실행됩니다(`pipeline.py:154-166`). `Guardrail Apply` 내부의 recomposer 루프는 최대 2회입니다(`pipeline.py:335-372`).

---

## 2. 시퀀스 다이어그램 (런타임 스트리밍)

```mermaid
sequenceDiagram
    autonumber
    actor U as 사용자
    participant UI as streamlit_app.py
    participant G as graph.stream()<br/>(build_analysis_graph)
    participant W as 병렬 워커
    participant GR as Guardrail 단계

    U->>UI: 투자성향 7단계 + 포트폴리오 입력
    UI->>G: stream_phase1_analysis_events(query, profile, portfolio)
    G->>G: ① Curator → ② RequestClassifier(worker_plan)
    Note over G,W: Send API fan-out (동적 병렬)
    G->>W: ③④⑤ Quant·Qual·Competitor (+⑥ Macro 조건부)
    W-->>G: 각 워커 결과 (실패 시 worker_errors 격리)
    G->>G: ⑦ Strategist join → ⑧ InvestmentAnalyst(sLLM)
    G->>GR: ⑨ Guardrail 7게이트
    alt needs_revision 또는 !passed
        GR->>GR: ⑩ recomposer 루프 (≤2회)
    end
    GR->>G: ⑪ ResultRenderer (Tier 1/2/3)
    G-->>UI: 노드별 이벤트 yield (placeholder 점진 갱신)
    UI-->>U: Tier 1 신호 + Tier 2 근거 + Tier 3 다운로드
```

> UI는 `graph.stream()`의 노드 단위 yield를 매 이벤트마다 placeholder로 점진 렌더합니다(`streamlit_app.py:425-448`).

---

## 3. 에러핸들링·폴백 요약

```mermaid
flowchart LR
    subgraph 격리["워커 실패 격리 (_safe_worker_node)"]
      WE["worker_errors 누적<br/>전체 크래시 방지"]
    end
    subgraph 합성["Strategist"]
      SF["가용 워커 1개만 있어도 진행<br/>전부 실패 시 conservative HOLD"]
    end
    subgraph 가드["Guardrail"]
      GF["예외 시 passed=False<br/>risk_level=high"]
    end
    격리 --> 합성 --> 가드
    class WE,SF,GF core;
    classDef core fill:#f1f5f9,color:#334155,stroke:#94a3b8;
```

근거: `pipeline.py:169-184`(격리) · `:225-258`(strategist 폴백) · `:266-290`(guardrail 폴백).

---

## 4. 사용처 (이 정본을 복붙할 대상)

| 대상 문서/HTML | 적용 다이어그램 |
|---|---|
| `README.md` 시스템 아키텍처 절 | §1 마스터 플로우차트 |
| `docs/architecture/multi_agent_architecture.md` | §1, §3 |
| `docs/architecture/system_flow.md` | §1, §2 |
| `docs/architecture/multi_agent_architecture_review.html` (Mermaid 교체) | §1 |
| `docs/architecture/system_architecture_dashboard.html` | §1 |
| `docs/ai/orchestration.md` (Phase 2) | §1, §2 |

> 교체 시 각 문서 상단에 `> 다이어그램 정본: docs/architecture/canonical_diagrams.md` 를 남긴다.

---

## 5. 유스케이스 다이어그램

> 상세: [`docs/usecase/usecase_spec.md`](../usecase/usecase_spec.md). 액터·유스케이스·외부 시스템 관계.

```mermaid
flowchart LR
    investor(("👤 개인 투자자"))
    evaluator(("🛠 평가 관리자"))

    subgraph SYS["stock-agent"]
      S1["UC-S1 투자성향 온보딩·프로필"]
      S2["UC-S2 포트폴리오 입력"]
      A1["UC-A1 보유 종목 검토"]
      A2["UC-A2 신규/추가 종목 추천"]
      A3["UC-A3 리스크 점검"]
      A4["UC-A4 매도 판단"]
      A5["UC-A5 포트폴리오 전반 점검"]
      O1["UC-O1 산출물 다운로드"]
      M1["UC-M1 골든셋 평가"]
    end

    investor --> S1 --> S2
    investor --> A1
    investor --> A2
    investor --> A3
    investor --> A4
    investor --> A5
    investor --> O1
    evaluator --> M1

    A1 -. include .-> S2
    A5 -. include .-> S2
    O1 -. extend .-> A1

    DART[("DART")]; KRX[("pykrx/KRX")]; NEWS[("뉴스")]; ECOS[("ECOS")]; MCP[("MCP peer")]; LLM[("LLM")]
    A1 --- DART
    A1 --- KRX
    A1 --- NEWS
    A2 --- MCP
    A5 --- ECOS
    A1 --- LLM

    classDef uc fill:#eff6ff,color:#1e3a8a,stroke:#2563eb;
    classDef ext fill:#f1f5f9,color:#334155,stroke:#94a3b8;
    class S1,S2,A1,A2,A3,A4,A5,O1,M1 uc;
    class DART,KRX,NEWS,ECOS,MCP,LLM ext;
```

> `include`(점선): 분석 유스케이스는 포트폴리오 입력을 전제로 한다. `extend`: 다운로드는 분석 결과가 있을 때 확장된다.
