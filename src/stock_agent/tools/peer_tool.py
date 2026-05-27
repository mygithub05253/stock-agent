from __future__ import annotations

from statistics import median

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
