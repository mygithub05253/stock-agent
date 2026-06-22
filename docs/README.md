# `docs/` — 프로젝트 문서

PM이 주로 관리하는 문서 영역입니다. 개발자도 자유롭게 읽고 PR로 의견 제시 가능.

## 폴더 소개

- **What:** PRD, 기능 명세, 아키텍처, 운영, 피드백, 로드맵, 발표 자료를 한곳에서 관리합니다.
- **Why:** Notion이나 대화에만 남은 결정을 코드와 함께 리뷰·버전 관리하기 위해 사용합니다.
- Markdown과 Mermaid를 정확한 원본으로 우선합니다.
- HTML은 발표·회의용 상호작용 시각화로 사용합니다.
- PNG/SVG와 실제 UI 캡처는 `assets/`와 `guides/`에 보관합니다.

## 문서 흐름

```mermaid
flowchart LR
    P[PRD] --> F[기능 명세]
    F --> A[아키텍처 / ADR]
    A --> I[구현]
    I --> E[평가 / 피드백]
    E --> R[로드맵 / 운영]
```

## 주요 결과

- 코드 기준 README 시스템 Mermaid와 GPT Image 2.0 요약 이미지를 제공합니다.
- 2026-06-12 Phase 1 평가 **40/41**, faithfulness **0.4096**을 기록합니다.
- 2026-06-14 Competitor 회귀 **6/6**을 기록합니다.
- 폴더별 README가 문서 책임과 갱신 규칙을 안내합니다.

## 폴더 구조

```
docs/
├── prd/                                    ← 요구사항 정의 (Product Requirements Document)
│   └── PRD_v0.6.md
├── functional-spec/                        ← 기능 명세서 (각 기능의 상세 동작)
│   ├── README.md                           ← 기능 명세 작성 규칙 / 인덱스
│   ├── overview/
│   │   └── functional_spec_all_features_v0.1.md
│   ├── basic/
│   │   ├── B1_signup_login_spec_v0.3.md
│   │   ├── B2_holdings_manage_spec_v0.4.md
│   │   ├── B3_stock_search_spec_v0.5.md
│   │   ├── B4_stock_basic_info_spec_v0.6.md
│   │   └── B5_portfolio_bulk_advice_spec_v0.2.md
│   ├── demo/
│   │   └── D1_backtesting_validation_spec_v0.1.md
│   └── advanced/
│       ├── A1_valuation_5y_spec_v0.7.md
│       ├── A2_industry_qualitative_spec_v0.8.md
│       ├── A3_peer_comparison_spec_v1.0.md
│       ├── A4_action_recommendation_spec_v1.0.md
│       └── A5_stock_recommendation_spec_v1.1.md
├── architecture/                           ← 시스템 설계
│   ├── README.md                           ← 구조 문서 인덱스
│   ├── readme_system_architecture.md       ← 현재 코드 기준 README Mermaid
│   ├── system_flow.md                      ← 사용자→에이전트→DB→출력 흐름도 (Mermaid)
│   ├── multi_agent_architecture.md         ← 개발팀용 멀티 에이전트 상세 설계
│   ├── multi_agent_architecture_review.html← 팀 논의용 멀티 에이전트 HTML 리뷰 문서
│   ├── api.html                            ← 위 HTML 문서로 이동하는 호환 링크
│   ├── system_architecture_dashboard.html  ← 전체 구조와 6 에이전트 흐름을 보는 인터랙티브 HTML 대시보드
│   ├── backtesting_demo_architecture.md    ← 5/22 타깃 예측일 기반 백테스팅 검증 설계
│   ├── backtesting_demo_dashboard.html     ← 백테스팅 검증 아키텍처 HTML 시각화
│   ├── erd.md                              ← DB ERD
│   └── agent_design.md                     ← 6 에이전트 상세 설계 진입 문서
├── operations/                             ← 운영 가이드
│   ├── db_connection_guide.md              ← 로컬/Supabase DB 연결 전환 가이드
│   ├── llm_cost_guide.md                   ← LLM 비용 절감 가이드
│   └── pm_workflow_guide.md                ← PM 문서 작성/협업 가이드
├── feedback/                               ← 외부 피드백 원문 + 갭 분석·대응 계획
│   ├── README.md                           ← 피드백 보관 규칙 / 인덱스
│   ├── 2026-05-31_강사검토리포트_d24b475.md ← 강사님 검토 리포트 원문 (20/70, 루브릭 10항목)
│   └── 2026-06-13_갭분석_파트별_강화계획_v1.0.md ← 피드백 대비 파트별 강화·구현 계획
├── decisions/                              ← ADR (Architecture Decision Records)
│   ├── ADR-001-data-arch-postgres-pgvector.md
│   ├── ADR-002-critic-separation-vs-merge.md
│   ├── ADR-003-six-agent-structure.md
│   └── ADR-004-monthly-cost-cap.md
├── roadmap/
│   ├── 2026-05-23/
│   │   └── roadmap_dashboard.html
│   └── 2026-06-12/
│       └── progress_dashboard.html         ← 루브릭 진행도 대시보드 (리포트→현재→목표)
├── notion/                                 ← 노션 원본/정리본 보관
│   ├── architecture.md
│   ├── database.md
│   └── images/
├── glossary.md                             ← 용어집 (비전공자용)
├── guides/                                 ← 사용 가이드와 UI 개선 제안
├── superpowers/                            ← 승인 설계와 구현 계획
└── assets/                                 ← 이미지·다이어그램 SVG/PNG 보관
    └── readme/                             ← README 썸네일·아키텍처·실제 캡처
```

## 주요 시각화 문서

| 문서 | 용도 |
|------|------|
| `docs/architecture/multi_agent_architecture_review.html` | 팀 회의에서 멀티 에이전트 구조, agent 책임, DB/Prompt/Tool/Guardrail을 한 화면에서 논의 |
| `docs/architecture/api.html` | `multi_agent_architecture_review.html`로 이동하는 짧은 호환 링크 |
| `docs/architecture/system_architecture_dashboard.html` | 전체 stock-agent 구조와 Agent 흐름 설명 |
| `docs/architecture/readme_system_architecture.md` | 현재 코드 기준 LangGraph·데이터 연결 Mermaid |
| `docs/assets/readme/stock-agent-architecture.png` | GPT Image 2.0 README 아키텍처 요약 이미지 |
| `docs/architecture/backtesting_demo_dashboard.html` | 2026-05-22 타깃 예측일 기반 백테스팅 시연 구조 설명 |
| `docs/assets/backtesting_demo_architecture.svg` | 발표 자료에 삽입 가능한 백테스팅 아키텍처 이미지 |

## 개발팀이 먼저 읽을 문서

| 순서 | 문서 | 왜 읽는가 |
|------|------|-----------|
| 1 | `docs/prd/PRD_v0.6.md` | 프로젝트가 해결하려는 문제, 범위, 성공 기준 확인 |
| 2 | `docs/architecture/readme_system_architecture.md` | 현재 Agent 실행과 DB/Tool/RAG 연결 확인 |
| 3 | `docs/architecture/system_flow.md` | 사용자 흐름, agent 흐름, 데이터 흐름을 Mermaid로 확인 |
| 4 | `docs/architecture/erd.md` | 실제 table과 agent별 데이터 사용 범위 확인 |
| 5 | `docs/operations/llm_cost_guide.md` | 모델 라우팅, 캐싱, 월 5만원 비용 상한 확인 |
| 6 | `docs/decisions/ADR-*.md` | 왜 Postgres+pgvector, 6-agent, 비용 상한을 선택했는지 확인 |

## 현재 구현 상태와 목표 상태

| 구분 | 현재 | 목표 |
|------|------|------|
| Graph | LangGraph `StateGraph` + Quant/Qual/Competitor/Macro 동적 병렬 fan-out | 병렬 지연·부분 실패 관측 강화 |
| Agent | DB/Tool/RAG/LLM 우선, 경로별 보수적 fallback | 근거 품질과 Input/Tool/Output Guardrail 강화 |
| RAG | PostgreSQL GIN + pgvector Hybrid Search 연결 | faithfulness 0.4096을 목표 0.80까지 개선 |
| Prompt | Agent 6종 `system.md` 분리 | prompt 변경 자동 평가 범위 확대 |
| Evaluation | 5개 페르소나 40/41, Competitor 6/6 | rule 100%와 RAGAS 목표 달성 |

## 문서 작성 규칙

1. **모든 새 문서는 PR로** — 노션·구글닥에 흩어두지 말고 git에 올린다.
2. **버전 표기 필수** — `v0.6`, `v1.0` 같은 버전을 파일명·문서 헤더 양쪽에 표기.
3. **Mermaid 우선** — 다이어그램은 가능한 Markdown 안의 mermaid 코드블록으로. PNG는 마지막 수단.
4. **용어 풀이 박스** — 새 약어 등장 시 첫 등장 부분에 풀이 추가 또는 `glossary.md` 갱신.
5. **변경 이력** — 문서 하단에 "변경 이력" 섹션 추가 (날짜·변경 요약).
