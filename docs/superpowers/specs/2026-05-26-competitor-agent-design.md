# Competitor Agent 코어 우선 MVP 설계서

| 항목 | 값 |
|------|-----|
| 작성일 | 2026-05-26 |
| 작업 브랜치 | `codex/competitor-agent-design` |
| 상태 | 사용자 승인 후 한국어 개정 |
| 주요 독자 | Competitor Agent 담당자, PM, 에이전트/백엔드 팀원 |
| 관련 문서 | `docs/functional-spec/advanced/A3_peer_comparison_spec_v0.9.md`, `docs/architecture/multi_agent_architecture.md`, `docs/architecture/system_flow.md`, `docs/architecture/erd.md` |

---

## 1. 결정 사항

Competitor Agent의 1차 MVP는 **코어 우선 실사용형**으로 구현한다.

이번 범위는 Streamlit UI까지 한 번에 붙이는 큰 PR이 아니라, 다른 에이전트가 의존할 수 있는 계산 코어와 입출력 계약을 먼저 고정하는 PR이다. `company`, `stock_price`, `financial_statement`에 있는 실제 DB 데이터를 사용해 국내 같은 섹터 peer를 추출하고, PER/PBR/ROE/성장률/마진 기반 상대 위치와 `competitor_score`를 계산한다.

UI는 다음 PR에서 붙인다. 이번 PR은 계산 신뢰도, schema 안정성, 테스트, 실험 노트북, PM 문서를 우선한다.

---

## 2. 목표

- `CuratorResult`의 `stock_code`, `corp_code`, `sector`를 기준으로 국내 같은 섹터 peer를 자동 선정한다.
- 대상 종목과 peer의 최신 시세와 재무 데이터를 불러와 비교 지표를 계산한다.
- LLM 없이도 재현 가능한 `CompetitorResult`를 생성한다.
- Strategist가 기존처럼 `score`, `peer_summary`, `peers`, `evidence`를 사용할 수 있게 호환성을 유지한다.
- 데이터 부족, peer 부족, 결측 지표를 결과에 명시해 Guardrail과 UI가 보수적으로 표시할 수 있게 한다.
- 팀원이 흐름을 검증할 수 있는 실험용 notebook과 PM용 문서를 남긴다.

---

## 3. 제외 범위

- 글로벌 peer 비교는 하지 않는다. MVP는 국내 같은 `company.sector` 중심이다.
- LLM이 새로운 숫자, 추정치, 멀티플을 만들게 하지 않는다.
- Streamlit 화면 구현은 이번 설계의 1차 구현 범위에서 제외한다.
- `analysis_cache`, `analysis_history` 저장은 향후 인터페이스를 염두에 두되 이번 코어 PR에서 필수 구현하지 않는다.
- Quant Agent의 5년 밸류에이션 전체 로직을 Competitor Agent 안으로 가져오지 않는다.

---

## 4. 전체 구조

```text
AgentState.curator
    |
    v
run_competitor(state)
    |
    v
peer_tool.build_peer_comparison(...)
    |
    +-- company: 대상 종목과 같은 섹터 peer 후보
    +-- stock_price: 최신 종가, 시가총액, 거래량
    +-- financial_statement: 최근 매출, 영업이익, 순이익, 자본, 부채
    |
    v
CompetitorResult
    |
    v
Strategist
```

역할 경계는 다음처럼 둔다.

| 계층 | 파일 | 책임 |
|------|------|------|
| Schema | `src/stock_agent/schemas/analysis.py` | agent, graph, test, 향후 UI가 공유할 안정적인 결과 계약 |
| 도구 | `src/stock_agent/tools/peer_tool.py` | DB 조회, 지표 계산, peer 정렬, 점수 계산 |
| 에이전트 | `src/stock_agent/agents/competitor.py` | 이전 단계 state 검증, peer 도구 호출, `CompetitorResult` 변환 |
| 프롬프트 | `src/stock_agent/prompts/competitor/system.md` | 향후 LLM 해석 규칙. MVP 계산은 LLM 없이 동작 |
| 테스트 | `tests/agents/test_competitor.py`, `tests/tools/test_peer_tool.py` | 계산식과 결과 계약 검증 |
| 노트북 | `notebooks/competitor_agent_walkthrough.ipynb` | PM/개발자용 실행 흐름 확인 |
| PM 문서 | `docs/agents/competitor_agent_mvp.md`, `docs/agents/competitor_agent_mvp.html` | 구현 내용, 검증 방법, 남은 작업 요약 |

---

## 5. 컴포넌트 설계

### 5.1 Schema

`CompetitorResult`는 현재 사용 중인 필드를 유지한다.

- `score`
- `peer_summary`
- `peers`
- `evidence`

A3 명세에 맞춰 다음 필드는 선택 필드로 확장한다.

- `peer_selection_summary`
- `metric_definitions`
- `relative_position`
- `data_quality_flags`
- `a1_peer_multiple_payload`
- `warnings`

호환성을 유지해야 하는 이유는 `streamlit_app.py`, `pipeline.py`, `run_strategist`가 이미 단순 필드를 사용하고 있기 때문이다.

### 5.2 도구

`peer_tool.py`는 하나의 큰 함수가 아니라 작은 함수들의 조합으로 작성한다.

권장 함수:

- `load_target_company(conn, stock_code)`
- `load_peer_candidates(conn, target, max_peer_count)`
- `load_latest_prices(conn, stock_codes)`
- `load_financial_snapshots(conn, corp_codes, lookback_years)`
- `calculate_peer_metrics(company_rows, price_rows, financial_rows)`
- `rank_peer_metrics(metric_rows, target_stock_code)`
- `build_peer_comparison(conn, stock_code, sector=None, min_peer_count=3, max_peer_count=8, lookback_years=3)`

도구는 `peer_tool.py` 안에 정의한 타입 명시 Pydantic model을 반환한다. 에이전트는 이 도구 model을 최종 `CompetitorResult`로 변환한다.

### 5.3 에이전트

`run_competitor(state)`는 다음 순서로 동작한다.

1. `state.curator`가 있는지 확인한다.
2. Curator가 확정한 `stock_code`와 `sector`를 사용한다.
3. `peer_tool`을 호출한다.
4. 도구 결과를 `CompetitorResult`로 변환한다.
5. DB 접근이 불가능한 Phase 1 데모 모드에서만 현재 mock과 유사한 대체 결과를 사용하고, 반드시 `mock_data_fallback` 경고를 남긴다.

대체 결과가 실제 운영 데이터처럼 보이면 안 된다.

### 5.4 프롬프트

`src/stock_agent/prompts/competitor/system.md`에는 향후 LLM 해석 규칙을 둔다.

- 도구가 제공한 값만 사용한다.
- peer 이름, 시가총액, PER, PBR, ROE, 성장률을 새로 만들지 않는다.
- peer 선정 기준을 설명한다.
- peer 수나 데이터 완성도가 낮으면 confidence를 낮춘다.
- 투자 권유로 오해될 표현을 피한다.

외부 GIC v11 프롬프트는 구조 참고용으로만 사용한다. 참고할 수 있는 요소는 peer mapping 기준, 표/CSV 정리 습관, 검증 태그, 출처/시점 의식이다. 그대로 복사하지 않는 이유는 우리 프로젝트가 챗봇 웹검색 리포트가 아니라 DB 기반 구조화 출력 시스템이기 때문이다.

---

## 6. 지표와 점수

최소 지표 세트는 다음과 같다.

| 지표 | 방향성 | 계산 출처 |
|------|--------|-----------|
| PER | 낮을수록 저평가 가능성이 높다. 단, 순이익이 0 이하이면 계산 제외 | 최신 시가총액 / 최신 순이익 |
| PBR | 낮을수록 저평가 가능성이 높다. 단, 자본이 없으면 계산 제외 | 최신 시가총액 / 최신 자본 |
| ROE | 높을수록 수익성이 좋다 | 최신 순이익 / 최신 자본 |
| 매출 성장률 | 높을수록 성장성이 좋다 | 최신 매출과 직전 비교 가능 연도 매출 |
| 영업이익률 | 높을수록 영업 수익성이 좋다 | 최신 영업이익 / 최신 매출 |
| 부채비율 | 낮을수록 재무 안정성이 좋다 | 최신 부채 / 최신 자본 |

점수 정책:

- 대상 종목과 선정된 peer 집합 안에서 지표별 순위와 분위수를 계산한다.
- 결측 지표는 보수적으로 처리한다.
- peer가 3개 미만이면 점수와 신뢰도를 낮춘다.
- 대상 종목의 데이터 완성도가 낮으면 강한 결론을 내지 않는다.
- 0~100점 `score`를 반환하며, 50점은 peer 대비 중립 위치로 본다.

MVP 점수 공식은 다음과 같다.

```text
score =
  20% valuation_position
+ 25% profitability_position
+ 20% growth_position
+ 15% margin_position
+ 10% balance_sheet_position
+ 10% data_quality
```

대상 종목에서 신뢰할 수 있는 지표가 3개 미만이면 강한 결론을 만들지 않고, 낮은 신뢰도의 중립 점수와 데이터 품질 경고를 반환한다.

---

## 7. 데이터 흐름

입력:

- `stock_code`
- 선택 입력 `corp_code`
- 선택 입력 `sector`
- `min_peer_count=3`
- `max_peer_count=8`
- `lookback_years=3`

DB 조회:

- `company`: 대상 종목과 같은 섹터 peer 후보
- `stock_price`: 최신 가격, 시가총액, 거래량
- `financial_statement`: 최근 매출, 영업이익, 순이익, 자본, 부채

출력:

- `CompetitorResult.score`
- `CompetitorResult.peer_summary`
- `CompetitorResult.peers`
- `CompetitorResult.evidence`
- 향후 UI와 A1 연계를 위한 선택 상세 필드

---

## 8. 예외 처리

| 상황 | 처리 |
|------|------|
| `state.curator`가 없음 | graph 순서 오류이므로 `ValueError` 발생 |
| 대상 종목을 찾을 수 없음 | `CompetitorResult(score=0, peer_summary=...)`와 `target_not_found` 경고 반환 |
| 대상 종목 섹터가 없음 | 자동 peer 추출을 하지 않고 낮은 점수와 `sector_missing` 경고 반환 |
| peer 후보가 3개 미만 | 가능한 peer만 비교하고 `peer_count_below_minimum` 경고 추가 |
| 시세 데이터 없음 | 해당 기업의 PER/PBR과 시총 정렬 제외, 경고 추가 |
| 재무 데이터 없음 | 해당 지표 제외. 대상 종목 핵심 재무가 없으면 insufficient data 결과 반환 |
| 분모가 0 이하 | 해당 지표를 `not_applicable`로 표시하고 임의 보간하지 않음 |
| DB 연결 불가 | 데모 모드에서만 명시적 mock 대체 결과 사용, `mock_data_fallback` 경고 추가 |

---

## 9. 테스트 전략

단위 테스트는 live DB 없이 동작해야 한다.

테스트 케이스:

- 같은 섹터 peer 선택 시 target stock이 제외된다.
- peer 정렬은 시가총액 근접도와 데이터 완성도를 반영한다.
- PER/PBR/ROE/성장률/마진 계산은 동일 입력에서 항상 같은 결과를 낸다.
- 순이익이 음수이면 PER은 `not_applicable`이 된다.
- peer가 3개 미만이면 경고와 낮은 confidence가 반환된다.
- `run_competitor`는 현재 Strategist가 사용하는 필드를 계속 제공한다.
- 기존 Phase 1 pipeline test가 계속 통과한다.

DB 연동 테스트를 추가할 경우 `DATABASE_URL`이 있을 때만 실행하고, 없으면 skip한다.

---

## 10. 노트북과 PM 문서

노트북은 production 기준 코드가 아니라 흐름 확인용이다.

노트북 섹션:

1. 샘플 target 로드
2. peer 후보 표시
3. 최신 시세와 재무 row 표시
4. 계산된 metric table 표시
5. 최종 `CompetitorResult` 표시
6. 경고와 다음 구현 단계 설명

PM 문서 섹션:

- Competitor Agent가 이제 무엇을 하는지
- 어떤 DB 테이블을 사용하는지
- peer 선정이 어떻게 이루어지는지
- score와 경고를 어떻게 해석해야 하는지
- MVP에서 의도적으로 제외한 범위
- 이후 UI가 이 결과를 어떻게 렌더링할 수 있는지

---

## 11. 구현 순서

1. 기존 필드 호환성을 유지하면서 schema를 확장한다.
2. `peer_tool.py`에 순수 계산 보조 함수를 만든다.
3. 계산 보조 함수 테스트를 추가한다.
4. DB 조회 보조 함수를 추가한다.
5. `run_competitor`가 도구를 사용하도록 바꾸고 명시적 대체 경로를 둔다.
6. 에이전트 단위 테스트를 추가한다.
7. Competitor 프롬프트 markdown을 추가한다.
8. 흐름 확인용 노트북을 추가한다.
9. PM 문서를 추가한다.
10. 가능한 범위에서 테스트와 lint를 실행한다.

---

## 12. 승인 기록

사용자는 2026-05-26에 다음 방향을 승인했다.

- MVP 실사용형 Competitor Agent를 만든다.
- 실무적으로는 코어 우선 경로를 우선한다.
- Streamlit UI는 구현 중 아주 작고 안전한 hook이 보이는 경우가 아니라면 다음 PR로 미룬다.

---

## 13. 자체 검토

- 미완성 표식 검사: 미완성 표식 없음.
- 일관성 검토: 이번 PR에서는 UI를 제외하되, UI가 바로 쓸 수 있는 상세 필드를 준비한다.
- 범위 검토: 첫 구현은 Competitor Agent 코어 PR 하나로 제한하며, 멀티 에이전트 전체 구조 변경으로 확장하지 않는다.
- 모호성 검토: 글로벌 peer, LLM 숫자 생성, 캐시 영구 저장은 이번 MVP PR 범위 밖으로 명시했다.
