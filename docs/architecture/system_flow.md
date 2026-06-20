# 시스템 흐름도

| 항목 | 값 |
|------|-----|
| 작성자 | PM |
| 작성일 | 2026-05-10 |
| 버전 | v0.1 |
| 상위 문서 | `docs/prd/PRD_v0.6.md` |

---

## 0. 이 문서를 보는 법

본 문서에는 **Mermaid 다이어그램** 4종이 들어 있습니다. GitHub·VSCode·Obsidian에서 자동으로 그림으로 렌더링됩니다.

> Mermaid가 안 보이고 코드만 보인다면, GitHub 웹에서 보거나 Mermaid 플러그인을 설치하세요. 변경 시 `https://mermaid.live` 에서 실시간 미리보기 가능.

비전공자 팀원께: 이 4장 흐름도를 보면 **시스템이 어떻게 동작하는지** 큰 그림을 잡을 수 있습니다. 코드를 안 봐도 됩니다.

| # | 다이어그램 | 어떤 시점에서 보면 좋은가 |
|---|-----------|---------------------------|
| 1 | **사용자 시나리오 흐름** (Sequence) | "사용자가 화면에서 어떤 순서로 행동하는가?" |
| 2 | **LangGraph 노드 흐름** (Flowchart) | "AI 에이전트들은 어떤 순서로 일하는가?" |
| 3 | **데이터 플로우** (Architecture) | "데이터가 어디서 와서 어디로 가는가?" |
| 4 | **12주 일정** (Gantt) | "언제 무엇을 하는가?" |

> 최신 멀티 에이전트 상세 설계와 팀 회의용 HTML은 `docs/architecture/multi_agent_architecture.md`,
> `docs/architecture/multi_agent_architecture_review.html`을 함께 참고한다.

---

## 0.1 현행 구현 상태 (11노드 LangGraph)

> 기준 코드(SSOT): [`pipeline_11node_groundtruth.md`](pipeline_11node_groundtruth.md) · 다이어그램 정본 [`canonical_diagrams.md`](canonical_diagrams.md). 본 문서 초안(2026-05-10)의 "mock 순차/목표" 기술은 아래로 갱신됨.

현재 코드는 **11노드 LangGraph `StateGraph`**가 실동작한다(`graph/pipeline.py:404-435`). classifier가 `worker_plan`을 정하고 Send API로 워커를 동적 병렬 실행, strategist에서 join한다.

```text
Curator → RequestClassifier → [Quant·Qual·Competitor (+Macro 조건부) 병렬]
→ Strategist(join) → InvestmentAnalyst → Guardrail → Guardrail Apply → ResultRenderer
```

| 영역 | 현행 |
|------|------|
| Graph | LangGraph `StateGraph` 11노드 컴파일 |
| 병렬화 | `_fanout_workers`(Send API) 동적 병렬, macro는 조건부 |
| 전문 Agent | DB/Tool/LLM/RAG 연결(워커별 try/except 격리) |
| RAG | Qual이 Hybrid RRF retriever 실호출 |
| sLLM | InvestmentAnalyst qwen-2.5-7b 보정 |
| Guardrail | 7게이트 + PII 차단 + recomposer revision loop(≤2) |

---

## 1. 사용자 시나리오 흐름 — 박민호 페르소나 (Sequence Diagram)

> 박민호(균형형 투자자)가 "내 포트에서 삼성전자 어떻게 할까?" 를 묻는 시나리오. 화면 → 시스템 → 화면의 흐름을 시간 순서대로.

```mermaid
sequenceDiagram
    actor U as 박민호 (사용자)
    participant H as streamlit_app.py (홈)
    participant Q as pages/1_분석_진행중
    participant R as pages/2_추천_결과
    participant D as pages/3_상세_산출물
    participant LG as LangGraph 파이프라인 (Streamlit 프로세스 내)
    participant DB as Postgres + pgvector

    U->>H: 로그인 (이메일/비밀번호)
    H->>DB: 사용자 조회
    DB-->>H: 프로필 + 포트폴리오
    H-->>U: 로그인 성공 + 홈 화면

    U->>H: "삼성전자 어떻게 할까?" 자연어 입력
    H->>Q: st.switch_page("pages/1_분석_진행중.py")

    Note over Q,LG: 백엔드에서 멀티에이전트 실행

    Q->>LG: AgentState 초기화
    LG->>LG: 1) Curator → RequestClassifier (worker_plan)
    LG->>LG: 2) Quant + Qual + Competitor (+Macro 조건부) 병렬
    LG->>LG: 3) Strategist join → InvestmentAnalyst (sLLM)
    LG->>LG: 4) Guardrail → Guardrail Apply (PII·재생성 ≤2)
    LG->>LG: 5) ResultRenderer (Tier 1/2/3)
    LG-->>Q: Tier 1/2/3 결과

    Q-->>U: 진행 상태 실시간 표시 (st.spinner + st.empty 갱신)

    U->>R: 분석 완료 → st.switch_page("pages/2_추천_결과.py")
    R-->>U: Tier 1 한 줄 (BUY 78% / 적합도 ★★★★)

    U->>R: "왜?" 클릭 → st.expander 펼침 (Tier 2)
    R-->>U: 5개 차원 근거 카드 (정량/정성/Peer/매크로/포트)

    U->>D: "PB 리포트 받기" 클릭 → st.switch_page("pages/3_상세_산출물.py")
    D->>D: WeasyPrint 로 PDF 생성 (Streamlit 프로세스 내)
    D-->>U: st.download_button → report.pdf 다운로드
```

---

## 2. LangGraph 노드 흐름 (Flowchart)

> AI 에이전트들이 어떤 순서로 협업하는지. **11노드** + Send API 동적 병렬 fan-out. (정본: [`canonical_diagrams.md`](canonical_diagrams.md) §1)

```mermaid
flowchart TD
    START([사용자 분석 요청]) --> CUR[🎯 Curator<br/>의도·종목 확정]
    CUR --> CLS[🧭 RequestClassifier<br/>worker_plan 결정]
    CLS -. "Send API" .-> FAN{동적 fan-out}

    FAN --> QNT[📊 Quant]
    FAN --> QAL[📰 Qual ★<br/>Hybrid RRF RAG]
    FAN --> CMP[🏢 Competitor<br/>DB→MCP→mock]
    FAN -. "조건부" .-> MAC[🌍 Macro]

    QNT --> STR((join))
    QAL --> STR
    CMP --> STR
    MAC --> STR

    STR --> SYN[🎲 Strategist<br/>가중 합성·자체검토]
    SYN --> INV[🤖 InvestmentAnalyst<br/>sLLM qwen-2.5-7b 보정]
    INV --> GRD[🛡 Guardrail<br/>7게이트·PII·RAGAS]
    GRD --> GAP[🔁 Guardrail Apply<br/>PII 차단 + revision loop ≤2]
    GAP --> RND[Tier 1/2/3 렌더링]
    RND --> ENDX([Streamlit 표시 + 다운로드])

    style QAL fill:#10b981,color:#fff
    style SYN fill:#ef4444,color:#fff
    style GRD fill:#6b7280,color:#fff
    style CUR fill:#f59e0b,color:#fff
    style QNT fill:#3b82f6,color:#fff
    style CMP fill:#8b5cf6,color:#fff
```

**핵심 설명:**
- 🎯 Curator → 🧭 RequestClassifier가 scope·depth로 `worker_plan`을 결정 (macro 포함 여부)
- 📊 Quant + 📰 Qual + 🏢 Competitor (+🌍 Macro 조건부) → **Send API 동적 병렬**. 실행된 워커만 join
- 🎲 Strategist → 가중 합성 + 자체 검토 → 🤖 InvestmentAnalyst가 sLLM으로 최종 보정 (Critic 분리 안 한 이유는 `ADR-002`)
- 🛡 Guardrail → 🔁 Guardrail Apply에서 PII 차단·recomposer 재생성 루프(≤2). 백그라운드 RAGAS 채점

---

## 3. 데이터 플로우 (Architecture Diagram)

> 데이터가 어디서 들어와서 → 어디에 저장되고 → 어떻게 쓰이는지.

```mermaid
flowchart LR
    subgraph "외부 데이터 소스"
        DART[(DART<br/>재무·공시)]
        PYKRX[pykrx<br/>시세·거래]
        NAVER[네이버금융·한경<br/>뉴스 크롤링]
        ECOS[ECOS·FRED<br/>매크로]
    end

    subgraph "데이터팀 영역 (datas/)"
        DC[datas/dart/<br/>collector]
        PC[datas/news/<br/>collector + Sanitizer]
        MC[datas/macro/<br/>collector]
    end

    DART --> DC
    PYKRX --> DC
    NAVER --> PC
    ECOS --> MC

    subgraph "저장소"
        PG[(🗄 Postgres<br/>정형 데이터<br/>company / financial_statement /<br/>disclosure_report / stock_price /<br/>users · holdings 설계안)]
        VEC[(🔍 pgvector tables<br/>rag_documents / rag_chunks<br/>뉴스·공시 본문<br/>+ 임베딩 벡터)]
    end

    DC -->|재무·공시 메타| PG
    PC -->|기사 메타| PG
    PC -->|기사 본문 + 임베딩| VEC
    DC -->|공시 본문 + 임베딩| VEC
    MC -->|매크로 시계열| PG

    subgraph "AI 에이전트 (src/stock_agent/)"
        CUR[Curator]
        QNT[Quant]
        QAL[Qual ★]
        CMP[Competitor]
        STR[Strategist]
        GRD[Guardrail]
    end

    PG -.조회.-> CUR
    PG -.재무 조회.-> QNT
    PG -.뉴스 메타.-> QAL
    VEC -.RAG 검색.-> QAL
    PG -.Peer 조회.-> CMP
    VEC -.공시 RAG.-> CMP
    PG -.매크로 조회.-> STR
    PG -.포트 조회.-> STR

    CUR --> STR
    QNT --> STR
    QAL --> STR
    CMP --> STR
    STR --> GRD

    subgraph "출력"
        UI[🖥 Streamlit UI<br/>Tier 1/2/3]
        XLS[📊 Excel 8시트<br/>밸류에이션]
        HTM[🌐 HTML<br/>산업·뉴스 분석]
        PDF[📘 PDF + DOCX<br/>PB 리포트]
    end

    GRD --> UI
    GRD --> XLS
    GRD --> HTM
    GRD --> PDF

    style QAL fill:#10b981,color:#fff
    style STR fill:#ef4444,color:#fff
    style GRD fill:#6b7280,color:#fff
    style PG fill:#336791,color:#fff
    style VEC fill:#ff6b35,color:#fff
```

**핵심 설명 (비전공자용):**
- **외부 → 데이터팀 → 저장소** 경로: 매일 한 번 (또는 사용자 요청 시) 데이터 수집 → 깨끗하게 정리 → DB에 적재
- **Postgres 안에서 역할을 나눈 이유**:
  - **Postgres (왼쪽 파란색)** = 표 형태로 잘 정리된 데이터 (회원·재무·시세·매크로)
  - **pgvector tables (오른쪽 주황)** = 긴 텍스트 + 의미 벡터를 Postgres 안에 저장 → "비슷한 뉴스 찾아줘" 가능
- **에이전트 → 저장소** 경로: 분석 요청이 오면 에이전트들이 필요한 데이터를 조회 → 결과를 만들어서 → 사용자에게 4가지 형태로 제공

---

## 4. 12주 일정 (Gantt Chart)

> 강사 가이드 12주 + 우리 작업 매핑

```mermaid
gantt
    title BDAI 12기 stock-agent 12주 로드맵
    dateFormat YYYY-MM-DD
    axisFormat %m/%d

    section 6주차 (이번 주)
    PRD v0.6 작성             :done, prd, 2026-05-09, 3d
    폴더 구조 + 협업 가이드    :done, struct, 2026-05-10, 1d
    기능 명세서 v0.1          :active, spec, 2026-05-11, 4d
    팀원 환경 셋업            :env, 2026-05-12, 3d

    section 7주차
    Postgres 스키마 적용       :db, 2026-05-15, 2d
    pgvector 인덱싱           :pgvector, 2026-05-16, 2d
    Quant Worker 첫 호출       :quant1, 2026-05-17, 3d
    Hello E2E 1종목           :e2e, 2026-05-19, 2d

    section 8주차
    회원가입·로그인            :auth, 2026-05-22, 2d
    종목 검색·기본정보         :search, 2026-05-23, 2d
    포트폴리오 일괄 안내        :port, 2026-05-25, 2d
    LangSmith 연동            :lang, 2026-05-26, 2d

    section 9주차
    중간 시연 준비             :demo, 2026-05-29, 2d
    중간 시연 + 피드백 수렴     :milestone, mid, 2026-05-31, 2d

    section 10주차
    A2A 패턴 도입             :a2a, 2026-06-05, 3d
    5y 밸류에이션 (Quant)      :val, 2026-06-06, 4d
    산업·정성 분석 (Qual)      :qual, 2026-06-07, 3d

    section 11주차
    동종업계 횡비교 (Comp)     :comp, 2026-06-12, 2d
    BUY/HOLD/SELL (Strat)     :decision, 2026-06-13, 3d
    PB 리포트 (PDF/DOCX)      :report, 2026-06-14, 3d
    README + BENCHMARK         :readme, 2026-06-16, 2d

    section 12주차
    Streamlit Cloud 배포       :deploy, 2026-06-19, 2d
    발표자료 + Q&A 대비        :slide, 2026-06-20, 2d
    팀별 최종 발표             :milestone, final, 2026-06-21, 1d
```

---

## 5. 부속 — 사용자가 보는 Tier 1/2/3 진행 (시각화)

> 분석 종료 후 사용자에게 *어떤 순서로 정보가 펼쳐지는지*

```mermaid
flowchart TD
    R[분석 완료] --> T1{Tier 1<br/>큰 글씨 한 줄}
    T1 --> T1A[BUY · 신뢰도 78%<br/>적합도 ★★★★☆<br/>적정주가 80,000원<br/>안전마진 18.8%]

    T1A -->|"왜?" 버튼 클릭| T2{Tier 2<br/>5개 근거 카드}
    T2 --> T2A[📊 정량 카드<br/>5y 밸류에이션 요약]
    T2 --> T2B[📰 정성 카드<br/>최근 호재/악재]
    T2 --> T2C[🏢 경쟁사 카드<br/>Peer 대비 위치]
    T2 --> T2D[🌍 매크로 카드<br/>금리·환율 영향]
    T2 --> T2E[💼 포트 카드<br/>내 비중·집중도]

    T2A & T2B & T2C & T2D & T2E -->|"더 깊이" 클릭| T3{Tier 3<br/>다운로드}
    T3 --> T3A[📄 report.pdf<br/>7페이지 PB 양식]
    T3 --> T3B[📝 report.docx<br/>편집용]
    T3 --> T3C[📊 valuation.xlsx<br/>5y 모델 8시트]
    T3 --> T3D[🌐 analysis.html<br/>산업/뉴스 인용]
```

**Progressive Disclosure (점진적 공개) 원칙**: Tier 1만 봐도 결정 가능. Tier 2는 "왜?" 의 답. Tier 3은 "더 깊이" 의 답. 인지부하 1/3로 줄임.

---

## 6. 부속 — 백테스팅 기반 시연 검증 흐름

> 중간 시연에서는 실제 미래 예측을 즉시 검증할 수 없으므로, 2026년 5월 22일을 타깃 예측일로 두고 AI 입력 데이터는 2026년 5월 21일 23:59 이전으로 마스킹한다.

```mermaid
flowchart LR
    subgraph S["Streamlit 설정"]
        A["종목: 삼성전자"]
        B["분석 단위: 1주/2주/4주"]
        C["타깃 예측일: 2026-05-22"]
    end

    subgraph M["마스킹/슬라이싱"]
        D["mask_datetime<br/>2026-05-21 23:59"]
        E["가격·뉴스·DART·매크로<br/>입력 기간 필터링"]
        F["5월 22일 이후 데이터 제외"]
    end

    subgraph AI["AI 판단"]
        G["Quant/Qual skeleton"]
        H["Strategist<br/>BUY/HOLD/SELL"]
        I["Guardrail<br/>미래 데이터 언급 차단"]
    end

    subgraph T["정답 대조"]
        J["2026-05-22 실제 OHLCV"]
        K["수익률·방향 적중 여부"]
    end

    A --> D
    B --> D
    C --> D
    D --> E --> F --> G --> H --> I
    J --> K
    I --> K
```

자세한 설계는 `docs/architecture/backtesting_demo_architecture.md`, 발표용 HTML은 `docs/architecture/backtesting_demo_dashboard.html`을 참고한다.

---

## 변경 이력

| 날짜 | 버전 | 변경 |
|------|------|------|
| 2026-06-20 | v0.3 | **11노드 정합** — §0.1 현행 상태, §1 시퀀스 단계, §2 노드 흐름도를 11노드 LangGraph(classifier·macro·investment_analyst·guardrail_apply·renderer 포함)로 갱신. 정본 다이어그램 연결 |
| 2026-05-23 | v0.2 | 5월 22일 타깃 예측일 기반 백테스팅 시연 검증 흐름 추가 |
| 2026-05-10 | v0.1 | 초안 — 4종 Mermaid (Sequence·Flowchart·Architecture·Gantt) + 보너스 Tier 다이어그램 |

