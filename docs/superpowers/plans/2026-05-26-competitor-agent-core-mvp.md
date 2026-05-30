# Competitor Agent 코어 우선 MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **팀 공유 원칙:** 설명 문서는 한국어로 작성한다. 코드 식별자, 파일명, schema field 이름은 기존 프로젝트와 호환되도록 영어를 유지한다.

**Goal:** `company`, `stock_price`, `financial_statement` DB 데이터를 사용해 국내 같은 섹터 peer를 선정하고, Competitor Agent가 재현 가능한 비교 점수와 근거를 반환하도록 만든다.

**Architecture:** `agents/competitor.py`는 판단 흐름만 담당하고, DB 조회와 계산은 `tools/peer_tool.py`로 분리한다. `schemas/analysis.py`의 기존 `CompetitorResult` 필드는 유지하면서 A3 명세에 필요한 선택 필드를 확장한다.

**Tech Stack:** Python 3.11, Pydantic v2, psycopg v3, pytest, Streamlit 기존 mock pipeline

---

## 0. 파일 구조와 책임

이번 구현에서 만들거나 수정할 파일은 다음과 같다.

| 파일 | 작업 | 책임 |
|------|------|------|
| `src/stock_agent/schemas/analysis.py` | 수정 | `CompetitorResult`에 A3 선택 필드 추가, 기존 호출부 호환 유지 |
| `src/stock_agent/tools/peer_tool.py` | 생성 | peer 후보 조회, 최신 시세 조회, 재무 snapshot 정규화, 지표 계산, 상대 점수 계산 |
| `src/stock_agent/agents/competitor.py` | 수정 | `peer_tool` 호출, DB 실패 시 명시적 demo fallback, `CompetitorResult` 생성 |
| `src/stock_agent/prompts/competitor/system.md` | 생성 | 향후 LLM 해석에 사용할 Competitor Agent 규칙 |
| `tests/test_competitor_schema.py` | 생성 | schema 확장 호환성 검증 |
| `tests/tools/test_peer_tool.py` | 생성 | DB 없이 순수 계산 함수 검증 |
| `tests/agents/test_competitor_agent.py` | 생성 | agent fallback과 tool 결과 변환 검증 |
| `docs/agents/competitor_agent_mvp.md` | 생성 | PM/팀원용 기능 설명 |
| `docs/agents/competitor_agent_mvp.html` | 생성 | 회의 공유용 간단 HTML 요약 |
| `notebooks/competitor_agent_walkthrough.ipynb` | 생성 | 실험 흐름 확인용 노트북 |

---

### Task 1: `CompetitorResult` schema 확장

**Files:**
- Modify: `src/stock_agent/schemas/analysis.py`
- Create: `tests/test_competitor_schema.py`

- [ ] **Step 1: schema 확장 실패 테스트 작성**

`tests/test_competitor_schema.py`를 생성한다.

```python
from stock_agent.schemas.analysis import CompetitorResult


def test_competitor_result_accepts_a3_optional_fields() -> None:
    result = CompetitorResult(
        score=62,
        peer_summary="Peer 대비 수익성은 중립, 재무 안정성은 우위입니다.",
        peers=[
            {
                "stock_code": "005930",
                "corp_name": "삼성전자",
                "per": 18.4,
                "pbr": 1.35,
                "roe": 7.8,
            }
        ],
        evidence=["PBR은 peer 중앙값과 유사합니다."],
        peer_selection_summary="같은 섹터에서 시가총액과 데이터 완성도를 기준으로 3개 peer를 선정했습니다.",
        metric_definitions={"per": "market_cap / net_income"},
        relative_position={"roe_percentile": 0.55, "valuation_percentile": 0.48},
        data_quality_flags=["peer_count_ok"],
        a1_peer_multiple_payload={"median_per": 18.4, "median_pbr": 1.35},
        warnings=["일부 peer의 성장률 데이터가 제한적입니다."],
    )

    assert result.score == 62
    assert result.peer_selection_summary is not None
    assert result.metric_definitions["per"] == "market_cap / net_income"
    assert result.relative_position["roe_percentile"] == 0.55
    assert result.data_quality_flags == ["peer_count_ok"]
    assert result.a1_peer_multiple_payload == {"median_per": 18.4, "median_pbr": 1.35}
    assert result.warnings == ["일부 peer의 성장률 데이터가 제한적입니다."]


def test_competitor_result_keeps_existing_minimal_contract() -> None:
    result = CompetitorResult(
        score=50,
        peer_summary="기존 최소 필드만으로도 생성됩니다.",
        peers=[],
        evidence=[],
    )

    assert result.score == 50
    assert result.peer_summary == "기존 최소 필드만으로도 생성됩니다."
    assert result.peer_selection_summary is None
    assert result.metric_definitions == {}
    assert result.relative_position == {}
    assert result.data_quality_flags == []
    assert result.a1_peer_multiple_payload is None
    assert result.warnings == []
```

- [ ] **Step 2: 실패 확인**

Run:

```bash
pytest tests/test_competitor_schema.py -v
```

Expected: `CompetitorResult`에 새 필드가 없어서 `ValidationError` 또는 unexpected keyword 관련 실패가 발생한다.

- [ ] **Step 3: schema 최소 구현**

`src/stock_agent/schemas/analysis.py`의 `CompetitorResult`만 아래처럼 교체한다.

```python
class CompetitorResult(BaseModel):
    score: int = Field(ge=0, le=100)
    peer_summary: str
    peers: list[dict[str, float | int | str | None]]
    evidence: list[str]
    peer_selection_summary: str | None = None
    metric_definitions: dict[str, str] = Field(default_factory=dict)
    relative_position: dict[str, float | int | str | None] = Field(default_factory=dict)
    data_quality_flags: list[str] = Field(default_factory=list)
    a1_peer_multiple_payload: dict[str, float | int | str | None] | None = None
    warnings: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: schema 테스트 통과 확인**

Run:

```bash
pytest tests/test_competitor_schema.py -v
```

Expected: `2 passed`

- [ ] **Step 5: 기존 pipeline 테스트 회귀 확인**

Run:

```bash
pytest tests/test_phase1_pipeline.py -v
```

Expected: 기존 2개 테스트가 통과한다.

- [ ] **Step 6: 커밋**

```bash
git add src/stock_agent/schemas/analysis.py tests/test_competitor_schema.py
git commit -m "✨ Feat: extend competitor result schema"
```

---

### Task 2: `peer_tool.py` 순수 계산 모델과 helper 구현

**Files:**
- Create: `src/stock_agent/tools/peer_tool.py`
- Create: `tests/tools/test_peer_tool.py`

- [ ] **Step 1: 계산 helper 실패 테스트 작성**

`tests/tools/` 폴더가 없으면 생성하고, `tests/tools/test_peer_tool.py`를 만든다.

```python
from stock_agent.tools.peer_tool import (
    CompanyPeer,
    FinancialSnapshot,
    PriceSnapshot,
    calculate_metric_row,
    calculate_relative_position,
    median_or_none,
)


def test_calculate_metric_row_uses_price_and_financial_data() -> None:
    company = CompanyPeer(
        corp_code="00126380",
        stock_code="005930",
        corp_name="삼성전자",
        sector="semiconductor",
    )
    price = PriceSnapshot(
        stock_code="005930",
        base_date="2026-05-25",
        close_price=70000,
        market_cap=420_000_000_000_000,
        volume=10_000_000,
    )
    latest = FinancialSnapshot(
        corp_code="00126380",
        bsns_year=2025,
        revenue=300_000_000_000_000,
        operating_income=30_000_000_000_000,
        net_income=21_000_000_000_000,
        equity=280_000_000_000_000,
        liabilities=70_000_000_000_000,
    )
    previous = FinancialSnapshot(
        corp_code="00126380",
        bsns_year=2024,
        revenue=250_000_000_000_000,
        operating_income=25_000_000_000_000,
        net_income=18_000_000_000_000,
        equity=260_000_000_000_000,
        liabilities=80_000_000_000_000,
    )

    row = calculate_metric_row(company, price, latest, previous)

    assert row.per == 20.0
    assert row.pbr == 1.5
    assert round(row.roe or 0, 4) == 0.075
    assert round(row.revenue_growth or 0, 4) == 0.2
    assert round(row.operating_margin or 0, 4) == 0.1
    assert round(row.debt_ratio or 0, 4) == 0.25
    assert row.data_quality_score == 100
    assert row.metric_flags == []


def test_negative_income_marks_per_not_applicable() -> None:
    company = CompanyPeer(corp_code="00000001", stock_code="000001", corp_name="적자기업", sector="test")
    price = PriceSnapshot(
        stock_code="000001",
        base_date="2026-05-25",
        close_price=1000,
        market_cap=100_000_000_000,
        volume=1000,
    )
    latest = FinancialSnapshot(
        corp_code="00000001",
        bsns_year=2025,
        revenue=10_000_000_000,
        operating_income=-1_000_000_000,
        net_income=-2_000_000_000,
        equity=5_000_000_000,
        liabilities=3_000_000_000,
    )

    row = calculate_metric_row(company, price, latest, None)

    assert row.per is None
    assert "per_not_applicable" in row.metric_flags
    assert "revenue_growth_missing" in row.metric_flags


def test_relative_position_scores_target_against_peers() -> None:
    rows = [
        calculate_metric_row(
            CompanyPeer(corp_code="1", stock_code="AAA001", corp_name="Target", sector="test"),
            PriceSnapshot(stock_code="AAA001", base_date="2026-05-25", close_price=1, market_cap=1000, volume=1),
            FinancialSnapshot(corp_code="1", bsns_year=2025, revenue=100, operating_income=20, net_income=10, equity=100, liabilities=20),
            FinancialSnapshot(corp_code="1", bsns_year=2024, revenue=90, operating_income=18, net_income=9, equity=90, liabilities=20),
        ),
        calculate_metric_row(
            CompanyPeer(corp_code="2", stock_code="BBB001", corp_name="Peer1", sector="test"),
            PriceSnapshot(stock_code="BBB001", base_date="2026-05-25", close_price=1, market_cap=800, volume=1),
            FinancialSnapshot(corp_code="2", bsns_year=2025, revenue=100, operating_income=10, net_income=8, equity=100, liabilities=40),
            FinancialSnapshot(corp_code="2", bsns_year=2024, revenue=95, operating_income=8, net_income=7, equity=90, liabilities=45),
        ),
    ]

    position = calculate_relative_position(rows, "AAA001")

    assert 0 <= position.score <= 100
    assert position.relative_position["roe_percentile"] >= 0.5
    assert position.relative_position["operating_margin_percentile"] >= 0.5


def test_median_or_none_ignores_none_values() -> None:
    assert median_or_none([None, 10.0, 20.0]) == 15.0
    assert median_or_none([None, None]) is None
```

- [ ] **Step 2: 실패 확인**

Run:

```bash
pytest tests/tools/test_peer_tool.py -v
```

Expected: `ModuleNotFoundError: No module named 'stock_agent.tools.peer_tool'`

- [ ] **Step 3: 순수 계산 구현**

`src/stock_agent/tools/peer_tool.py`를 아래 내용으로 생성한다.

```python
from __future__ import annotations

from statistics import median
from typing import Any

from pydantic import BaseModel, Field


class CompanyPeer(BaseModel):
    corp_code: str
    stock_code: str
    corp_name: str
    sector: str | None = None


class PriceSnapshot(BaseModel):
    stock_code: str
    base_date: str
    close_price: int | None = None
    market_cap: int | None = None
    volume: int | None = None


class FinancialSnapshot(BaseModel):
    corp_code: str
    bsns_year: int
    revenue: int | None = None
    operating_income: int | None = None
    net_income: int | None = None
    equity: int | None = None
    liabilities: int | None = None


class PeerMetricRow(BaseModel):
    corp_code: str
    stock_code: str
    corp_name: str
    sector: str | None = None
    base_date: str | None = None
    bsns_year: int | None = None
    market_cap: int | None = None
    close_price: int | None = None
    volume: int | None = None
    per: float | None = None
    pbr: float | None = None
    roe: float | None = None
    revenue_growth: float | None = None
    operating_margin: float | None = None
    debt_ratio: float | None = None
    data_quality_score: int = Field(ge=0, le=100)
    metric_flags: list[str] = Field(default_factory=list)


class PeerPosition(BaseModel):
    score: int = Field(ge=0, le=100)
    relative_position: dict[str, float | int | str | None]
    evidence: list[str]
    data_quality_flags: list[str]
    a1_peer_multiple_payload: dict[str, float | int | str | None] | None = None


def safe_div(numerator: int | float | None, denominator: int | float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return float(numerator) / float(denominator)


def rounded(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def median_or_none(values: list[float | None]) -> float | None:
    clean_values = [value for value in values if value is not None]
    if not clean_values:
        return None
    return float(median(clean_values))


def _quality_score(values: list[float | int | None]) -> int:
    filled = sum(value is not None for value in values)
    return round((filled / len(values)) * 100)


def _percentile(values: list[float], target: float, higher_is_better: bool) -> float:
    if not values:
        return 0.5
    better_or_equal = sum(value <= target for value in values)
    percentile = better_or_equal / len(values)
    if not higher_is_better:
        percentile = 1 - percentile + (1 / len(values))
    return max(0.0, min(1.0, percentile))


def _metric_percentile(rows: list[PeerMetricRow], target: PeerMetricRow, metric: str, higher_is_better: bool) -> float:
    values = [getattr(row, metric) for row in rows]
    numeric_values = [float(value) for value in values if value is not None]
    target_value = getattr(target, metric)
    if target_value is None or not numeric_values:
        return 0.5
    return _percentile(numeric_values, float(target_value), higher_is_better)


def calculate_metric_row(
    company: CompanyPeer,
    price: PriceSnapshot | None,
    latest: FinancialSnapshot | None,
    previous: FinancialSnapshot | None,
) -> PeerMetricRow:
    flags: list[str] = []

    market_cap = price.market_cap if price else None
    close_price = price.close_price if price else None
    volume = price.volume if price else None
    base_date = price.base_date if price else None

    revenue = latest.revenue if latest else None
    operating_income = latest.operating_income if latest else None
    net_income = latest.net_income if latest else None
    equity = latest.equity if latest else None
    liabilities = latest.liabilities if latest else None

    per = safe_div(market_cap, net_income) if net_income and net_income > 0 else None
    if per is None:
        flags.append("per_not_applicable")

    pbr = safe_div(market_cap, equity) if equity and equity > 0 else None
    if pbr is None:
        flags.append("pbr_not_applicable")

    roe = safe_div(net_income, equity) if equity and equity > 0 else None
    if roe is None:
        flags.append("roe_missing")

    previous_revenue = previous.revenue if previous else None
    revenue_growth = None
    if revenue is not None and previous_revenue and previous_revenue > 0:
        revenue_growth = (revenue - previous_revenue) / previous_revenue
    else:
        flags.append("revenue_growth_missing")

    operating_margin = safe_div(operating_income, revenue) if revenue and revenue > 0 else None
    if operating_margin is None:
        flags.append("operating_margin_missing")

    debt_ratio = safe_div(liabilities, equity) if equity and equity > 0 else None
    if debt_ratio is None:
        flags.append("debt_ratio_missing")

    quality = _quality_score([market_cap, close_price, revenue, operating_income, net_income, equity, liabilities])

    return PeerMetricRow(
        corp_code=company.corp_code,
        stock_code=company.stock_code,
        corp_name=company.corp_name,
        sector=company.sector,
        base_date=base_date,
        bsns_year=latest.bsns_year if latest else None,
        market_cap=market_cap,
        close_price=close_price,
        volume=volume,
        per=rounded(per, 4),
        pbr=rounded(pbr, 4),
        roe=rounded(roe, 4),
        revenue_growth=rounded(revenue_growth, 4),
        operating_margin=rounded(operating_margin, 4),
        debt_ratio=rounded(debt_ratio, 4),
        data_quality_score=quality,
        metric_flags=flags,
    )


def calculate_relative_position(rows: list[PeerMetricRow], target_stock_code: str) -> PeerPosition:
    target = next(row for row in rows if row.stock_code == target_stock_code)

    valuation_position = (
        _metric_percentile(rows, target, "per", higher_is_better=False)
        + _metric_percentile(rows, target, "pbr", higher_is_better=False)
    ) / 2
    profitability_position = _metric_percentile(rows, target, "roe", higher_is_better=True)
    growth_position = _metric_percentile(rows, target, "revenue_growth", higher_is_better=True)
    margin_position = _metric_percentile(rows, target, "operating_margin", higher_is_better=True)
    balance_sheet_position = _metric_percentile(rows, target, "debt_ratio", higher_is_better=False)
    data_quality = target.data_quality_score / 100

    score = round(
        (valuation_position * 20)
        + (profitability_position * 25)
        + (growth_position * 20)
        + (margin_position * 15)
        + (balance_sheet_position * 10)
        + (data_quality * 10)
    )

    flags = list(target.metric_flags)
    if len(rows) < 4:
        flags.append("peer_count_below_minimum")
        score = max(0, score - 8)
    if target.data_quality_score < 60:
        flags.append("target_data_quality_low")
        score = min(score, 55)

    peer_rows = [row for row in rows if row.stock_code != target_stock_code]
    median_per = median_or_none([row.per for row in peer_rows])
    median_pbr = median_or_none([row.pbr for row in peer_rows])

    relative_position: dict[str, float | int | str | None] = {
        "valuation_percentile": rounded(valuation_position),
        "roe_percentile": rounded(profitability_position),
        "growth_percentile": rounded(growth_position),
        "operating_margin_percentile": rounded(margin_position),
        "balance_sheet_percentile": rounded(balance_sheet_position),
        "data_quality_score": target.data_quality_score,
    }

    evidence = [
        f"{target.corp_name}의 peer 대비 valuation 위치는 {round(valuation_position * 100)} 분위입니다.",
        f"ROE 기준 peer 내 위치는 {round(profitability_position * 100)} 분위입니다.",
        f"데이터 완성도 점수는 {target.data_quality_score}점입니다.",
    ]

    return PeerPosition(
        score=max(0, min(100, score)),
        relative_position=relative_position,
        evidence=evidence,
        data_quality_flags=flags,
        a1_peer_multiple_payload={"median_per": median_per, "median_pbr": median_pbr},
    )
```

- [ ] **Step 4: 계산 테스트 통과 확인**

Run:

```bash
pytest tests/tools/test_peer_tool.py -v
```

Expected: `4 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/stock_agent/tools/peer_tool.py tests/tools/test_peer_tool.py
git commit -m "✨ Feat: add peer metric calculation tool"
```

---

### Task 3: DB 조회 helper와 `build_peer_comparison` 추가

**Files:**
- Modify: `src/stock_agent/tools/peer_tool.py`
- Modify: `tests/tools/test_peer_tool.py`

- [ ] **Step 1: DB 없이 정렬/요약을 검증하는 테스트 추가**

`tests/tools/test_peer_tool.py` 하단에 아래 테스트를 추가한다.

```python
from stock_agent.tools.peer_tool import (
    PeerMetricRow,
    build_peer_summary,
    select_peer_rows,
)


def test_select_peer_rows_excludes_target_and_prefers_quality_then_market_cap_proximity() -> None:
    target = PeerMetricRow(
        corp_code="1",
        stock_code="AAA001",
        corp_name="Target",
        sector="test",
        market_cap=1000,
        close_price=10,
        data_quality_score=100,
    )
    close_peer = PeerMetricRow(
        corp_code="2",
        stock_code="BBB001",
        corp_name="ClosePeer",
        sector="test",
        market_cap=900,
        close_price=9,
        data_quality_score=100,
    )
    weak_peer = PeerMetricRow(
        corp_code="3",
        stock_code="CCC001",
        corp_name="WeakPeer",
        sector="test",
        market_cap=980,
        close_price=9,
        data_quality_score=20,
    )

    selected = select_peer_rows(target, [target, weak_peer, close_peer], max_peer_count=1)

    assert [row.stock_code for row in selected] == ["BBB001"]


def test_build_peer_summary_mentions_peer_count_and_warnings() -> None:
    target = PeerMetricRow(
        corp_code="1",
        stock_code="AAA001",
        corp_name="Target",
        sector="test",
        market_cap=1000,
        close_price=10,
        data_quality_score=50,
        metric_flags=["roe_missing"],
    )

    summary = build_peer_summary(target, peer_count=2, data_quality_flags=["peer_count_below_minimum"])

    assert "Target" in summary
    assert "2개 peer" in summary
    assert "제한적" in summary
```

- [ ] **Step 2: 실패 확인**

Run:

```bash
pytest tests/tools/test_peer_tool.py::test_select_peer_rows_excludes_target_and_prefers_quality_then_market_cap_proximity tests/tools/test_peer_tool.py::test_build_peer_summary_mentions_peer_count_and_warnings -v
```

Expected: `ImportError` 또는 함수가 아직 없어 실패가 발생한다.

- [ ] **Step 3: `peer_tool.py`에 DB helper와 비교 builder 추가**

`src/stock_agent/tools/peer_tool.py` 하단에 아래 코드를 추가한다.

```python
from psycopg import Connection
from psycopg.rows import dict_row


ACCOUNT_ALIASES = {
    "revenue": ("매출액", "영업수익", "수익(매출액)"),
    "operating_income": ("영업이익",),
    "net_income": ("당기순이익", "분기순이익", "반기순이익"),
    "equity": ("자본총계",),
    "liabilities": ("부채총계",),
}


class PeerComparison(BaseModel):
    target: PeerMetricRow
    peers: list[PeerMetricRow]
    score: int = Field(ge=0, le=100)
    peer_selection_summary: str
    peer_summary: str
    metric_definitions: dict[str, str]
    relative_position: dict[str, float | int | str | None]
    evidence: list[str]
    data_quality_flags: list[str]
    a1_peer_multiple_payload: dict[str, float | int | str | None] | None = None
    warnings: list[str] = Field(default_factory=list)


def _fetch_all(conn: Connection, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return list(cur.fetchall())


def _fetch_one(conn: Connection, query: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    rows = _fetch_all(conn, query, params)
    return rows[0] if rows else None


def load_target_company(conn: Connection, stock_code: str) -> CompanyPeer | None:
    row = _fetch_one(
        conn,
        """
        SELECT corp_code, stock_code, corp_name, sector
        FROM company
        WHERE stock_code = %s
        """,
        (stock_code,),
    )
    return CompanyPeer(**row) if row else None


def load_peer_candidates(conn: Connection, target: CompanyPeer, max_peer_count: int = 8) -> list[CompanyPeer]:
    if not target.sector:
        return []
    rows = _fetch_all(
        conn,
        """
        SELECT corp_code, stock_code, corp_name, sector
        FROM company
        WHERE sector = %s
          AND stock_code IS NOT NULL
          AND stock_code <> %s
        ORDER BY corp_name
        LIMIT %s
        """,
        (target.sector, target.stock_code, max_peer_count * 4),
    )
    return [CompanyPeer(**row) for row in rows]


def load_latest_prices(conn: Connection, stock_codes: list[str]) -> dict[str, PriceSnapshot]:
    if not stock_codes:
        return {}
    rows = _fetch_all(
        conn,
        """
        SELECT DISTINCT ON (stock_code)
            stock_code,
            base_date::text AS base_date,
            close_price,
            market_cap,
            volume
        FROM stock_price
        WHERE stock_code = ANY(%s)
        ORDER BY stock_code, base_date DESC
        """,
        (stock_codes,),
    )
    return {row["stock_code"]: PriceSnapshot(**row) for row in rows}


def _classify_account(account_nm: str) -> str | None:
    compact_name = account_nm.replace(" ", "")
    for field, aliases in ACCOUNT_ALIASES.items():
        if any(alias.replace(" ", "") in compact_name for alias in aliases):
            return field
    return None


def load_financial_snapshots(
    conn: Connection,
    corp_codes: list[str],
    lookback_years: int = 3,
) -> dict[str, tuple[FinancialSnapshot | None, FinancialSnapshot | None]]:
    if not corp_codes:
        return {}
    rows = _fetch_all(
        conn,
        """
        SELECT corp_code, bsns_year, account_nm, amount
        FROM financial_statement
        WHERE corp_code = ANY(%s)
        ORDER BY corp_code, bsns_year DESC
        """,
        (corp_codes,),
    )

    grouped: dict[str, dict[int, dict[str, int | None]]] = {}
    for row in rows:
        field = _classify_account(row["account_nm"])
        if field is None:
            continue
        corp_code = row["corp_code"]
        year = int(row["bsns_year"])
        grouped.setdefault(corp_code, {}).setdefault(year, {})[field] = row["amount"]

    snapshots: dict[str, tuple[FinancialSnapshot | None, FinancialSnapshot | None]] = {}
    for corp_code, yearly_values in grouped.items():
        years = sorted(yearly_values.keys(), reverse=True)[:lookback_years]
        converted = [
            FinancialSnapshot(corp_code=corp_code, bsns_year=year, **yearly_values[year])
            for year in years
        ]
        latest = converted[0] if converted else None
        previous = converted[1] if len(converted) > 1 else None
        snapshots[corp_code] = (latest, previous)
    return snapshots


def select_peer_rows(
    target: PeerMetricRow,
    rows: list[PeerMetricRow],
    max_peer_count: int,
) -> list[PeerMetricRow]:
    candidates = [row for row in rows if row.stock_code != target.stock_code]

    def sort_key(row: PeerMetricRow) -> tuple[int, float]:
        if target.market_cap and row.market_cap:
            market_cap_gap = abs(row.market_cap - target.market_cap) / target.market_cap
        else:
            market_cap_gap = 9_999.0
        return (-row.data_quality_score, market_cap_gap)

    return sorted(candidates, key=sort_key)[:max_peer_count]


def build_peer_summary(
    target: PeerMetricRow,
    peer_count: int,
    data_quality_flags: list[str],
) -> str:
    if "peer_count_below_minimum" in data_quality_flags:
        return f"{target.corp_name}은 현재 {peer_count}개 peer만 비교 가능해 결과 해석이 제한적입니다."
    if "target_data_quality_low" in data_quality_flags:
        return f"{target.corp_name}은 일부 핵심 지표가 부족해 peer 대비 위치를 보수적으로 해석해야 합니다."
    return f"{target.corp_name}은 {peer_count}개 peer 기준으로 상대 위치를 계산했습니다."


def metric_definitions() -> dict[str, str]:
    return {
        "per": "latest_market_cap / latest_net_income, net_income <= 0이면 not_applicable",
        "pbr": "latest_market_cap / latest_equity",
        "roe": "latest_net_income / latest_equity",
        "revenue_growth": "(latest_revenue - previous_revenue) / previous_revenue",
        "operating_margin": "latest_operating_income / latest_revenue",
        "debt_ratio": "latest_liabilities / latest_equity",
    }


def build_peer_comparison(
    conn: Connection,
    stock_code: str,
    sector: str | None = None,
    min_peer_count: int = 3,
    max_peer_count: int = 8,
    lookback_years: int = 3,
) -> PeerComparison:
    target_company = load_target_company(conn, stock_code)
    if target_company is None:
        target = PeerMetricRow(
            corp_code="unknown",
            stock_code=stock_code,
            corp_name=stock_code,
            sector=sector,
            data_quality_score=0,
            metric_flags=["target_not_found"],
        )
        return PeerComparison(
            target=target,
            peers=[],
            score=0,
            peer_selection_summary="대상 종목을 company 테이블에서 찾지 못했습니다.",
            peer_summary="지원하지 않는 종목이어서 peer 비교를 수행하지 못했습니다.",
            metric_definitions=metric_definitions(),
            relative_position={},
            evidence=[],
            data_quality_flags=["target_not_found"],
            warnings=["target_not_found"],
        )

    if sector and not target_company.sector:
        target_company = target_company.model_copy(update={"sector": sector})

    candidate_companies = load_peer_candidates(conn, target_company, max_peer_count=max_peer_count)
    all_companies = [target_company, *candidate_companies]
    prices = load_latest_prices(conn, [company.stock_code for company in all_companies])
    financials = load_financial_snapshots(
        conn,
        [company.corp_code for company in all_companies],
        lookback_years=lookback_years,
    )

    rows: list[PeerMetricRow] = []
    for company in all_companies:
        latest, previous = financials.get(company.corp_code, (None, None))
        rows.append(calculate_metric_row(company, prices.get(company.stock_code), latest, previous))

    target_row = next(row for row in rows if row.stock_code == stock_code)
    peer_rows = select_peer_rows(target_row, rows, max_peer_count=max_peer_count)
    selected_rows = [target_row, *peer_rows]
    position = calculate_relative_position(selected_rows, stock_code)

    flags = list(position.data_quality_flags)
    if len(peer_rows) < min_peer_count and "peer_count_below_minimum" not in flags:
        flags.append("peer_count_below_minimum")
    if target_company.sector is None:
        flags.append("sector_missing")

    peer_selection_summary = (
        f"{target_company.sector or '섹터 미확인'} 섹터에서 "
        f"시가총액 근접도와 데이터 완성도를 기준으로 {len(peer_rows)}개 peer를 선정했습니다."
    )

    return PeerComparison(
        target=target_row,
        peers=peer_rows,
        score=position.score,
        peer_selection_summary=peer_selection_summary,
        peer_summary=build_peer_summary(target_row, len(peer_rows), flags),
        metric_definitions=metric_definitions(),
        relative_position=position.relative_position,
        evidence=position.evidence,
        data_quality_flags=flags,
        a1_peer_multiple_payload=position.a1_peer_multiple_payload,
        warnings=flags,
    )
```

- [ ] **Step 4: tool 테스트 통과 확인**

Run:

```bash
pytest tests/tools/test_peer_tool.py -v
```

Expected: `6 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/stock_agent/tools/peer_tool.py tests/tools/test_peer_tool.py
git commit -m "✨ Feat: add peer comparison builder"
```

---

### Task 4: `run_competitor`를 실제 tool 기반으로 연결

**Files:**
- Modify: `src/stock_agent/agents/competitor.py`
- Create: `tests/agents/test_competitor_agent.py`

- [ ] **Step 1: agent 테스트 작성**

`tests/agents/` 폴더가 없으면 생성하고, `tests/agents/test_competitor_agent.py`를 만든다.

```python
from stock_agent.agents import competitor as competitor_module
from stock_agent.agents.competitor import run_competitor
from stock_agent.schemas.analysis import (
    AgentState,
    CuratorResult,
    Portfolio,
    UserProfile,
)
from stock_agent.tools.peer_tool import PeerComparison, PeerMetricRow


class DummyConnection:
    pass


class DummyConnectionManager:
    def __enter__(self) -> DummyConnection:
        return DummyConnection()

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None


def _state() -> AgentState:
    return AgentState(
        user_query="삼성전자 peer 비교",
        user_profile=UserProfile(),
        portfolio=Portfolio(),
        curator=CuratorResult(
            intent="peer_compare",
            corp_name="삼성전자",
            stock_code="005930",
            corp_code="00126380",
            sector="semiconductor",
        ),
    )


def test_run_competitor_uses_peer_tool_result(monkeypatch) -> None:
    target = PeerMetricRow(
        corp_code="00126380",
        stock_code="005930",
        corp_name="삼성전자",
        sector="semiconductor",
        market_cap=420_000_000_000_000,
        data_quality_score=100,
    )
    peer = PeerMetricRow(
        corp_code="00164779",
        stock_code="000660",
        corp_name="SK하이닉스",
        sector="semiconductor",
        market_cap=150_000_000_000_000,
        per=22.0,
        pbr=1.8,
        roe=0.1,
        data_quality_score=100,
    )

    def fake_get_connection() -> DummyConnectionManager:
        return DummyConnectionManager()

    def fake_build_peer_comparison(conn, stock_code, sector=None):
        assert stock_code == "005930"
        assert sector == "semiconductor"
        return PeerComparison(
            target=target,
            peers=[peer],
            score=68,
            peer_selection_summary="semiconductor 섹터에서 1개 peer를 선정했습니다.",
            peer_summary="삼성전자는 1개 peer 기준으로 상대 위치를 계산했습니다.",
            metric_definitions={"per": "latest_market_cap / latest_net_income"},
            relative_position={"roe_percentile": 0.5},
            evidence=["ROE 기준 peer 내 위치는 50 분위입니다."],
            data_quality_flags=["peer_count_below_minimum"],
            a1_peer_multiple_payload={"median_per": 22.0, "median_pbr": 1.8},
            warnings=["peer_count_below_minimum"],
        )

    monkeypatch.setattr(competitor_module, "get_connection", fake_get_connection)
    monkeypatch.setattr(competitor_module, "build_peer_comparison", fake_build_peer_comparison)

    result_state = run_competitor(_state())

    assert result_state.competitor is not None
    assert result_state.competitor.score == 68
    assert result_state.competitor.peers[0]["corp_name"] == "SK하이닉스"
    assert result_state.competitor.peer_selection_summary == "semiconductor 섹터에서 1개 peer를 선정했습니다."
    assert result_state.competitor.warnings == ["peer_count_below_minimum"]


def test_run_competitor_raises_without_curator() -> None:
    state = AgentState(user_query="peer 비교", user_profile=UserProfile(), portfolio=Portfolio())

    try:
        run_competitor(state)
    except ValueError as exc:
        assert "curator result is required" in str(exc)
    else:
        raise AssertionError("run_competitor should require curator output")


def test_run_competitor_uses_explicit_mock_fallback_when_db_fails(monkeypatch) -> None:
    def fake_get_connection():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(competitor_module, "get_connection", fake_get_connection)

    result_state = run_competitor(_state())

    assert result_state.competitor is not None
    assert "mock_data_fallback" in result_state.competitor.warnings
    assert result_state.competitor.peer_selection_summary is not None
```

- [ ] **Step 2: 실패 확인**

Run:

```bash
pytest tests/agents/test_competitor_agent.py -v
```

Expected: 현재 `run_competitor`가 `peer_tool`을 쓰지 않아 monkeypatch 대상이 없거나 새 필드가 채워지지 않아 실패한다.

- [ ] **Step 3: `competitor.py` 구현 교체**

`src/stock_agent/agents/competitor.py` 전체를 아래 내용으로 교체한다.

```python
from stock_agent.db import get_connection
from stock_agent.schemas.analysis import AgentState, CompetitorResult
from stock_agent.tools.peer_tool import PeerComparison, build_peer_comparison


def _peer_row_to_dict(row) -> dict[str, float | int | str | None]:
    return {
        "stock_code": row.stock_code,
        "corp_code": row.corp_code,
        "corp_name": row.corp_name,
        "sector": row.sector,
        "market_cap": row.market_cap,
        "close_price": row.close_price,
        "per": row.per,
        "pbr": row.pbr,
        "roe": row.roe,
        "revenue_growth": row.revenue_growth,
        "operating_margin": row.operating_margin,
        "debt_ratio": row.debt_ratio,
        "data_quality_score": row.data_quality_score,
    }


def _result_from_comparison(comparison: PeerComparison) -> CompetitorResult:
    return CompetitorResult(
        score=comparison.score,
        peer_summary=comparison.peer_summary,
        peers=[_peer_row_to_dict(row) for row in comparison.peers],
        evidence=comparison.evidence,
        peer_selection_summary=comparison.peer_selection_summary,
        metric_definitions=comparison.metric_definitions,
        relative_position=comparison.relative_position,
        data_quality_flags=comparison.data_quality_flags,
        a1_peer_multiple_payload=comparison.a1_peer_multiple_payload,
        warnings=comparison.warnings,
    )


def _mock_fallback_result(reason: str) -> CompetitorResult:
    warnings = ["mock_data_fallback", reason]
    return CompetitorResult(
        score=64,
        peer_summary="DB 연결이 불가능해 Phase 1 데모용 mock peer 비교를 표시합니다.",
        peers=[
            {"corp_name": "삼성전자", "per": 18.4, "pbr": 1.35, "roe": 7.8},
            {"corp_name": "SK하이닉스", "per": 22.7, "pbr": 1.92, "roe": 8.5},
            {"corp_name": "DB하이텍", "per": 11.8, "pbr": 0.88, "roe": 6.4},
        ],
        evidence=[
            "이 결과는 실제 DB 계산값이 아니라 데모 fallback입니다.",
            "실제 peer 비교는 company, stock_price, financial_statement 연결 시 계산됩니다.",
        ],
        peer_selection_summary="DB 연결 실패로 mock peer 3개를 사용했습니다.",
        metric_definitions={
            "mock": "실제 계산식이 아닌 Phase 1 데모용 값입니다.",
        },
        relative_position={},
        data_quality_flags=["mock_data_fallback"],
        a1_peer_multiple_payload=None,
        warnings=warnings,
    )


def run_competitor(state: AgentState) -> AgentState:
    if state.curator is None:
        raise ValueError("curator result is required before competitor analysis")

    try:
        with get_connection() as conn:
            comparison = build_peer_comparison(
                conn,
                stock_code=state.curator.stock_code,
                sector=state.curator.sector,
            )
        state.competitor = _result_from_comparison(comparison)
    except Exception as exc:
        state.competitor = _mock_fallback_result(f"{exc.__class__.__name__}: {exc}")

    return state
```

- [ ] **Step 4: agent 테스트 통과 확인**

Run:

```bash
pytest tests/agents/test_competitor_agent.py -v
```

Expected: `3 passed`

- [ ] **Step 5: 전체 기존 테스트 회귀 확인**

Run:

```bash
pytest tests/test_phase1_pipeline.py tests/test_competitor_schema.py tests/tools/test_peer_tool.py tests/agents/test_competitor_agent.py -v
```

Expected: 모든 테스트 통과

- [ ] **Step 6: 커밋**

```bash
git add src/stock_agent/agents/competitor.py tests/agents/test_competitor_agent.py
git commit -m "✨ Feat: connect competitor agent to peer tool"
```

---

### Task 5: Competitor 프롬프트와 PM 문서 추가

**Files:**
- Create: `src/stock_agent/prompts/competitor/system.md`
- Create: `docs/agents/competitor_agent_mvp.md`
- Create: `docs/agents/competitor_agent_mvp.html`

- [ ] **Step 1: 프롬프트 폴더 생성**

Run:

```bash
New-Item -ItemType Directory -Force -Path src/stock_agent/prompts/competitor
New-Item -ItemType Directory -Force -Path docs/agents
```

Expected: 두 폴더가 생성된다. 이미 있으면 그대로 통과한다.

- [ ] **Step 2: system prompt 작성**

`src/stock_agent/prompts/competitor/system.md`를 생성한다.

```markdown
# Competitor Agent System Prompt

너는 한국 주식 분석 시스템의 Competitor Agent다.

## 역할

- 대상 기업을 국내 같은 섹터 peer와 비교한다.
- peer 선정 기준, 비교 가능한 지표, 결측 지표를 명확히 설명한다.
- 최종 판단은 투자 권유가 아니라 분석 신호의 근거로만 제공한다.

## 사용할 수 있는 데이터

- `peer_tool.py`가 제공한 peer 목록
- `peer_tool.py`가 계산한 PER, PBR, ROE, 매출 성장률, 영업이익률, 부채비율
- `peer_tool.py`가 제공한 데이터 품질 경고

## 금지 사항

- peer 기업명을 새로 만들지 않는다.
- PER, PBR, ROE, 성장률, 시가총액을 새로 만들지 않는다.
- 글로벌 peer를 임의로 추가하지 않는다.
- 출처 없는 단정, 수익 보장, 직접 매수/매도 지시를 하지 않는다.

## 출력 원칙

- peer 수가 3개 미만이면 비교 신뢰도가 낮다고 말한다.
- 결측 지표는 결측이라고 말한다.
- 좋은 점과 약한 점을 함께 설명한다.
- Strategist가 사용할 수 있게 핵심 근거를 짧고 명확하게 쓴다.
```

- [ ] **Step 3: PM 문서 작성**

`docs/agents/competitor_agent_mvp.md`를 생성한다.

```markdown
# Competitor Agent MVP 설명서

| 항목 | 내용 |
|------|------|
| 목적 | 국내 같은 섹터 peer를 선정하고 대상 종목의 상대 위치를 계산한다. |
| 주요 파일 | `src/stock_agent/agents/competitor.py`, `src/stock_agent/tools/peer_tool.py`, `src/stock_agent/schemas/analysis.py` |
| 사용 DB | `company`, `stock_price`, `financial_statement` |
| LLM 사용 | MVP 계산은 LLM 없이 동작한다. LLM은 향후 문장 해석에만 사용한다. |

## 동작 흐름

1. Curator Agent가 대상 종목과 섹터를 확정한다.
2. Competitor Agent가 `peer_tool.py`를 호출한다.
3. `peer_tool.py`가 같은 섹터 기업을 후보로 가져온다.
4. 최신 시세와 최근 재무 snapshot을 조회한다.
5. PER, PBR, ROE, 매출 성장률, 영업이익률, 부채비율을 계산한다.
6. 대상 종목의 peer 대비 상대 위치와 점수를 계산한다.
7. Strategist가 사용할 수 있는 `CompetitorResult`를 반환한다.

## 해석 방법

- `score` 50점은 peer 대비 중립 위치다.
- 70점 이상은 peer 대비 강점이 비교적 많은 상태다.
- 40점 이하는 peer 대비 약점이나 데이터 부족이 큰 상태다.
- `warnings`와 `data_quality_flags`가 있으면 점수보다 경고를 먼저 확인한다.

## MVP 제외 범위

- 글로벌 peer 비교
- LLM이 수치를 추정하는 방식
- 분석 캐시 저장
- Streamlit 상세 화면

## UI 연결 아이디어

- Tier 2의 Peer 탭에 `peer_summary`를 표시한다.
- peer 표에는 `corp_name`, `per`, `pbr`, `roe`, `revenue_growth`, `operating_margin`을 표시한다.
- `warnings`가 있으면 노란색 데이터 품질 배지로 표시한다.
```

- [ ] **Step 4: HTML 요약 작성**

`docs/agents/competitor_agent_mvp.html`를 생성한다.

```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Competitor Agent MVP</title>
  <style>
    body { font-family: Arial, "Noto Sans KR", sans-serif; margin: 32px; color: #111827; }
    h1 { font-size: 28px; margin-bottom: 8px; }
    h2 { margin-top: 28px; font-size: 20px; }
    .grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    .card { border: 1px solid #d1d5db; border-radius: 8px; padding: 16px; }
    code { background: #f3f4f6; padding: 2px 5px; border-radius: 4px; }
    li { margin: 6px 0; }
  </style>
</head>
<body>
  <h1>Competitor Agent MVP</h1>
  <p>국내 같은 섹터 peer를 선정하고 대상 종목의 상대 위치를 계산하는 코어 기능입니다.</p>

  <div class="grid">
    <div class="card"><strong>입력</strong><br><code>stock_code</code>, <code>sector</code></div>
    <div class="card"><strong>DB</strong><br><code>company</code>, <code>stock_price</code>, <code>financial_statement</code></div>
    <div class="card"><strong>출력</strong><br><code>CompetitorResult</code></div>
  </div>

  <h2>핵심 원칙</h2>
  <ul>
    <li>국내 같은 섹터 peer만 사용합니다.</li>
    <li>PER/PBR/ROE 등 수치는 Python 계산 결과만 사용합니다.</li>
    <li>peer 부족과 결측 지표는 경고로 남깁니다.</li>
    <li>Streamlit 상세 UI는 다음 PR에서 연결합니다.</li>
  </ul>
</body>
</html>
```

- [ ] **Step 5: 문서 파일 존재 확인**

Run:

```bash
Test-Path src/stock_agent/prompts/competitor/system.md
Test-Path docs/agents/competitor_agent_mvp.md
Test-Path docs/agents/competitor_agent_mvp.html
```

Expected: 세 줄 모두 `True`

- [ ] **Step 6: 커밋**

```bash
git add src/stock_agent/prompts/competitor/system.md docs/agents/competitor_agent_mvp.md docs/agents/competitor_agent_mvp.html
git commit -m "📝 Docs: add competitor agent prompt and guide"
```

---

### Task 6: 실험용 notebook 추가

**Files:**
- Create: `notebooks/competitor_agent_walkthrough.ipynb`

- [ ] **Step 1: notebooks 폴더 생성**

Run:

```bash
New-Item -ItemType Directory -Force -Path notebooks
```

Expected: `notebooks` 폴더가 생성된다. 이미 있으면 그대로 통과한다.

- [ ] **Step 2: notebook JSON 생성**

`notebooks/competitor_agent_walkthrough.ipynb`를 생성한다.

```json
{
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "# Competitor Agent Walkthrough\\n",
        "\\n",
        "이 노트북은 Competitor Agent의 peer 비교 흐름을 팀원이 확인하기 위한 실험용 문서입니다. production 코드는 `src/stock_agent/tools/peer_tool.py`와 `src/stock_agent/agents/competitor.py`를 기준으로 합니다."
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 1. 샘플 입력\\n",
        "\\n",
        "- target: 삼성전자 `005930`\\n",
        "- 목적: 같은 섹터 peer 후보와 비교 지표가 어떻게 만들어지는지 확인"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": null,
      "metadata": {},
      "outputs": [],
      "source": [
        "from stock_agent.graph import build_demo_profile\\n",
        "from stock_agent.schemas.analysis import AgentState, CuratorResult\\n",
        "from stock_agent.agents.competitor import run_competitor\\n",
        "\\n",
        "profile, portfolio = build_demo_profile()\\n",
        "state = AgentState(\\n",
        "    user_query='삼성전자 peer 비교',\\n",
        "    user_profile=profile,\\n",
        "    portfolio=portfolio,\\n",
        "    curator=CuratorResult(\\n",
        "        intent='peer_compare',\\n",
        "        corp_name='삼성전자',\\n",
        "        stock_code='005930',\\n",
        "        corp_code='00126380',\\n",
        "        sector='semiconductor',\\n",
        "    ),\\n",
        ")\\n",
        "state\\n"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 2. Competitor Agent 실행\\n",
        "\\n",
        "로컬 DB가 연결되어 있으면 실제 DB 기반 결과가 나오고, DB가 없으면 명시적 mock fallback 경고가 표시됩니다."
      ]
    },
    {
      "cell_type": "code",
      "execution_count": null,
      "metadata": {},
      "outputs": [],
      "source": [
        "result_state = run_competitor(state)\\n",
        "result_state.competitor.model_dump()\\n"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 3. 확인 포인트\\n",
        "\\n",
        "- `warnings`에 `mock_data_fallback`이 있으면 실제 DB 결과가 아닙니다.\\n",
        "- `data_quality_flags`가 있으면 peer 수나 재무/시세 결측을 먼저 확인합니다.\\n",
        "- Strategist는 `score`, `peer_summary`, `peers`, `evidence`를 우선 사용합니다."
      ]
    }
  ],
  "metadata": {
    "kernelspec": {
      "display_name": "Python 3",
      "language": "python",
      "name": "python3"
    },
    "language_info": {
      "name": "python",
      "version": "3.11"
    }
  },
  "nbformat": 4,
  "nbformat_minor": 5
}
```

- [ ] **Step 3: notebook JSON 유효성 확인**

Run:

```bash
python -m json.tool notebooks/competitor_agent_walkthrough.ipynb
```

Expected: JSON이 출력되고 오류가 없다.

- [ ] **Step 4: 커밋**

```bash
git add notebooks/competitor_agent_walkthrough.ipynb
git commit -m "📝 Docs: add competitor agent walkthrough notebook"
```

---

### Task 7: 전체 검증과 마무리

**Files:**
- Verify: `src/stock_agent/schemas/analysis.py`
- Verify: `src/stock_agent/tools/peer_tool.py`
- Verify: `src/stock_agent/agents/competitor.py`
- Verify: `tests/`
- Verify: `docs/agents/`
- Verify: `notebooks/`

- [ ] **Step 1: 전체 테스트 실행**

Run:

```bash
pytest -v
```

Expected: 모든 테스트 통과. DB가 없는 환경에서도 fallback 덕분에 Phase 1 pipeline은 통과해야 한다.

- [ ] **Step 2: ruff 실행**

Run:

```bash
ruff check src tests
```

Expected: `All checks passed!`

If ruff reports import order or line length issues, fix the exact reported file and run the same command again.

- [ ] **Step 3: 작업트리 확인**

Run:

```bash
git status --short --branch
```

Expected: 현재 브랜치가 `codex/competitor-agent-design`이고, 의도한 변경만 남아 있다.

- [ ] **Step 4: 문서 한국어 확인**

Run:

```bash
rg -n "작성 예정|나중에 작성|확인 필요|빈칸" docs/agents docs/superpowers/plans docs/superpowers/specs
```

Expected: 결과가 없다.

- [ ] **Step 5: 최종 커밋이 필요한 변경이 있으면 커밋**

```bash
git add src tests docs notebooks
git commit -m "✅ Test: verify competitor agent MVP"
```

Expected: 변경이 없으면 `nothing to commit`이 나올 수 있다. 변경이 있으면 검증 보정 커밋이 생성된다.

---

## 자체 검토

- 설계서 요구사항 대응: schema 확장, tool 분리, 실제 DB 조회, LLM 숫자 생성 금지, fallback 경고, 테스트, 노트북, PM 문서가 모두 task에 포함되어 있다.
- 미완성 표식 검사: 문제 없음.
- 타입 일관성: `PeerComparison`, `PeerMetricRow`, `CompetitorResult`의 필드 이름이 task 전반에서 동일하다.
- 범위 제한: Streamlit 상세 UI, 글로벌 peer, 분석 캐시 저장은 계획에 포함하지 않았다.
