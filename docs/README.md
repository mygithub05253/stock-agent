# `docs/` — 프로젝트 문서

PM이 주로 관리하는 문서 영역입니다. 개발자도 자유롭게 읽고 PR로 의견 제시 가능.

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
│   └── advanced/
│       ├── A1_valuation_5y_spec_v0.7.md
│       ├── A2_industry_qualitative_spec_v0.8.md
│       ├── A3_peer_comparison_spec_v0.9.md
│       ├── A4_action_recommendation_spec_v1.0.md
│       └── A5_stock_recommendation_spec_v1.1.md
├── architecture/                           ← 시스템 설계
│   ├── system_flow.md                      ← 사용자→에이전트→DB→출력 흐름도 (Mermaid)
│   └── erd.md                              ← DB ERD
│   ├── system_architecture_dashboard.html  ← 전체 구조와 6 에이전트 흐름을 보는 인터랙티브 HTML 대시보드
│   ├── erd.md                              ← DB ERD (4개 테이블)
│   └── agent_design.md                     ← 6 에이전트 상세 설계
├── operations/                             ← 운영 가이드
│   ├── db_connection_guide.md              ← 로컬/Supabase DB 연결 전환 가이드
│   ├── llm_cost_guide.md                   ← LLM 비용 절감 가이드
│   └── pm_workflow_guide.md                ← PM 문서 작성/협업 가이드
├── decisions/                              ← ADR (Architecture Decision Records)
│   ├── ADR-001-data-arch-postgres-pgvector.md
│   ├── ADR-002-critic-separation-vs-merge.md
│   ├── ADR-003-six-agent-structure.md
│   └── ADR-004-monthly-cost-cap.md
├── roadmap/
│   └── 2026-05-23/
│       └── roadmap_dashboard.html
│   ├── ADR-002-six-agent-structure.md
│   └── ADR-003-cost-cap-50k-monthly.md
├── notion/                                 ← 노션 원본/정리본 보관
│   ├── architecture.md
│   ├── database.md
│   └── images/
├── glossary.md                             ← 용어집 (비전공자용)
└── assets/                                 ← 이미지·다이어그램 PNG 보관
```

## 문서 작성 규칙

1. **모든 새 문서는 PR로** — 노션·구글닥에 흩어두지 말고 git에 올린다.
2. **버전 표기 필수** — `v0.6`, `v1.0` 같은 버전을 파일명·문서 헤더 양쪽에 표기.
3. **Mermaid 우선** — 다이어그램은 가능한 Markdown 안의 mermaid 코드블록으로. PNG는 마지막 수단.
4. **용어 풀이 박스** — 새 약어 등장 시 첫 등장 부분에 풀이 추가 또는 `glossary.md` 갱신.
5. **변경 이력** — 문서 하단에 "변경 이력" 섹션 추가 (날짜·변경 요약).
