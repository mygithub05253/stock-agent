from __future__ import annotations

from statistics import median
from typing import Any

from pydantic import BaseModel, Field

try:
    from psycopg import Connection
    from psycopg.rows import dict_row
except ModuleNotFoundError:
    Connection = Any  # type: ignore[misc,assignment]
    dict_row = None  # type: ignore[assignment]


ACCOUNT_ALIASES: dict[str, tuple[str, ...]] = {
    "revenue": ("매출액", "영업수익", "수익(매출액)"),
    "operating_income": ("영업이익",),
    "net_income": ("당기순이익", "당기순손익", "분기순이익", "반기순이익"),
    "equity": ("자본총계",),
    "liabilities": ("부채총계",),
}

PEER_SUMMARY_FLAG_MESSAGES: dict[str, str] = {
    "no_comparable_peers": "비교 가능한 peer가 없어 상대 위치를 계산하지 못했습니다.",
    "peer_count_below_minimum": "비교 가능한 peer 수가 부족해 결과 해석이 제한적입니다.",
    "sector_missing": "섹터 정보가 없어 자동 peer 선정이 제한되었습니다.",
    "target_data_quality_low": "대상 종목의 핵심 지표가 부족해 점수를 보수적으로 해석해야 합니다.",
    "per_not_applicable": "순이익 기준의 PER 비교가 제한되었습니다.",
    "pbr_not_applicable": "자본총계 기준의 PBR 비교가 제한되었습니다.",
    "roe_missing": "ROE 산출에 필요한 지표가 부족합니다.",
    "revenue_growth_missing": "매출 성장률 산출에 필요한 전년 비교 데이터가 부족합니다.",
    "operating_margin_missing": "영업이익률 산출에 필요한 지표가 부족합니다.",
    "debt_ratio_missing": "부채비율 산출에 필요한 지표가 부족합니다.",
}

UNKNOWN_PEER_SUMMARY_FLAG_MESSAGE = "일부 데이터 품질 이슈가 있어 세부 지표 해석에 주의가 필요합니다."


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
    values = [getattr(row, metric) for row in rows if row.stock_code != target.stock_code]
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
    peer_rows = [row for row in rows if row.stock_code != target_stock_code]

    if not peer_rows:
        flags = _dedupe([*target.metric_flags, "no_comparable_peers", "peer_count_below_minimum"])
        return PeerPosition(
            score=0,
            relative_position={
                "valuation_percentile": None,
                "roe_percentile": None,
                "growth_percentile": None,
                "operating_margin_percentile": None,
                "balance_sheet_percentile": None,
                "data_quality_score": target.data_quality_score,
            },
            evidence=[
                f"{target.corp_name}은 비교 가능한 peer가 없어 상대 위치를 계산하지 못했습니다.",
                f"데이터 완성도 점수는 {target.data_quality_score}점입니다.",
            ],
            data_quality_flags=flags,
            a1_peer_multiple_payload={"median_per": None, "median_pbr": None},
        )

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
        f"{target.corp_name}의 peer 대비 밸류에이션 위치는 {round(valuation_position * 100)}분위입니다.",
        f"ROE 기준 peer 대비 위치는 {round(profitability_position * 100)}분위입니다.",
        f"데이터 완성도 점수는 {target.data_quality_score}점입니다.",
    ]

    return PeerPosition(
        score=max(0, min(100, score)),
        relative_position=relative_position,
        evidence=evidence,
        data_quality_flags=flags,
        a1_peer_multiple_payload={"median_per": median_per, "median_pbr": median_pbr},
    )


def _fetch_all(conn: Connection, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    if dict_row is None:
        raise RuntimeError("psycopg is required to load peer comparison data from the DB.")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def _fetch_one(conn: Connection, query: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    if dict_row is None:
        raise RuntimeError("psycopg is required to load peer comparison data from the DB.")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row else None


def load_target_company(conn: Connection, stock_code: str) -> CompanyPeer | None:
    row = _fetch_one(
        conn,
        """
        SELECT corp_code, stock_code, corp_name, sector
        FROM company
        WHERE stock_code = %s
        LIMIT 1
        """,
        (stock_code,),
    )
    if row is None:
        return None
    return CompanyPeer(
        corp_code=str(row["corp_code"]),
        stock_code=str(row["stock_code"]),
        corp_name=str(row["corp_name"]),
        sector=str(row["sector"]) if row.get("sector") else None,
    )


def load_peer_candidates(
    conn: Connection,
    target: CompanyPeer,
    max_peer_count: int = 8,
) -> list[CompanyPeer]:
    if not target.sector:
        return []

    candidate_limit = max(max_peer_count * 4, 20)
    rows = _fetch_all(
        conn,
        """
        SELECT corp_code, stock_code, corp_name, sector
        FROM company
        WHERE sector = %s
          AND stock_code IS NOT NULL
          AND stock_code <> %s
        ORDER BY corp_name ASC
        LIMIT %s
        """,
        (target.sector, target.stock_code, candidate_limit),
    )
    return [
        CompanyPeer(
            corp_code=str(row["corp_code"]),
            stock_code=str(row["stock_code"]),
            corp_name=str(row["corp_name"]),
            sector=str(row["sector"]) if row.get("sector") else None,
        )
        for row in rows
    ]


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def load_latest_prices(conn: Connection, stock_codes: list[str]) -> dict[str, PriceSnapshot]:
    unique_stock_codes = list(dict.fromkeys(stock_codes))
    if not unique_stock_codes:
        return {}

    rows = _fetch_all(
        conn,
        """
        SELECT stock_code, base_date, close_price, market_cap, volume
        FROM stock_price
        WHERE stock_code = ANY(%s)
        ORDER BY stock_code ASC, base_date DESC
        """,
        (unique_stock_codes,),
    )

    snapshots: dict[str, PriceSnapshot] = {}
    for row in rows:
        stock_code = str(row["stock_code"])
        if stock_code in snapshots:
            continue
        snapshots[stock_code] = PriceSnapshot(
            stock_code=stock_code,
            base_date=str(row["base_date"]),
            close_price=_as_int(row.get("close_price")),
            market_cap=_as_int(row.get("market_cap")),
            volume=_as_int(row.get("volume")),
        )
    return snapshots


def _normalize_account_name(account_nm: str) -> str:
    return "".join(account_nm.strip().split())


def _classify_account(account_nm: str) -> str | None:
    normalized = _normalize_account_name(account_nm)
    if not normalized:
        return None

    for metric, aliases in ACCOUNT_ALIASES.items():
        for alias in aliases:
            normalized_alias = _normalize_account_name(alias)
            if normalized == normalized_alias or normalized_alias in normalized:
                return metric
    return None


def _financial_row_priority(row: dict[str, Any]) -> tuple[int, int, int]:
    return (
        0 if row.get("amount") is not None else 1,
        0 if row.get("reprt_code") == "11011" else 1,
        0 if row.get("fs_div") == "CFS" else 1,
    )


def load_financial_snapshots(
    conn: Connection,
    corp_codes: list[str],
    lookback_years: int = 3,
) -> dict[str, tuple[FinancialSnapshot | None, FinancialSnapshot | None]]:
    unique_corp_codes = list(dict.fromkeys(corp_codes))
    result: dict[str, tuple[FinancialSnapshot | None, FinancialSnapshot | None]] = {
        corp_code: (None, None) for corp_code in unique_corp_codes
    }
    if not unique_corp_codes:
        return result

    rows = _fetch_all(
        conn,
        """
        SELECT corp_code, bsns_year, reprt_code, fs_div, account_nm, amount
        FROM financial_statement
        WHERE corp_code = ANY(%s)
        ORDER BY corp_code ASC, bsns_year DESC
        """,
        (unique_corp_codes,),
    )

    best_rows: dict[tuple[str, int, str], dict[str, Any]] = {}
    for row in rows:
        metric = _classify_account(str(row.get("account_nm") or ""))
        if metric is None:
            continue

        corp_code = str(row["corp_code"])
        bsns_year = int(row["bsns_year"])
        key = (corp_code, bsns_year, metric)
        if key not in best_rows:
            best_rows[key] = row
            continue
        if _financial_row_priority(row) < _financial_row_priority(best_rows[key]):
            best_rows[key] = row

    values_by_corp_year: dict[str, dict[int, dict[str, int | None]]] = {}
    for (corp_code, bsns_year, metric), row in best_rows.items():
        year_values = values_by_corp_year.setdefault(corp_code, {}).setdefault(bsns_year, {})
        year_values[metric] = _as_int(row.get("amount"))

    for corp_code in unique_corp_codes:
        yearly_values = values_by_corp_year.get(corp_code, {})
        years = sorted(yearly_values, reverse=True)[:lookback_years]
        snapshots = [
            FinancialSnapshot(
                corp_code=corp_code,
                bsns_year=year,
                revenue=yearly_values[year].get("revenue"),
                operating_income=yearly_values[year].get("operating_income"),
                net_income=yearly_values[year].get("net_income"),
                equity=yearly_values[year].get("equity"),
                liabilities=yearly_values[year].get("liabilities"),
            )
            for year in years
        ]
        latest = snapshots[0] if snapshots else None
        previous = snapshots[1] if len(snapshots) > 1 else None
        result[corp_code] = (latest, previous)

    return result



_MARKET_CAP_BAND_LOW = 0.25
_MARKET_CAP_BAND_HIGH = 4.0


def _mark_outliers(rows: list[PeerMetricRow], target_stock_code: str) -> list[PeerMetricRow]:
    """peer 중앙값의 10배 초과 지표에 outlier_<metric> 플래그를 추가한다."""
    metrics = ["per", "pbr", "roe", "revenue_growth", "operating_margin", "debt_ratio"]
    peer_rows = [r for r in rows if r.stock_code != target_stock_code]

    result: list[PeerMetricRow] = []
    for row in rows:
        flags = list(row.metric_flags)
        for metric in metrics:
            val = getattr(row, metric)
            if val is None:
                continue
            others = [
                getattr(p, metric)
                for p in peer_rows
                if p.stock_code != row.stock_code and getattr(p, metric) is not None
            ]
            med = median_or_none(others)
            if med is not None and med != 0 and abs(val) > abs(med) * 10:
                flag = f"outlier_{metric}"
                if flag not in flags:
                    flags.append(flag)
        result.append(row if flags == row.metric_flags else row.model_copy(update={"metric_flags": flags}))
    return result


def select_peer_rows(
    target: PeerMetricRow,
    rows: list[PeerMetricRow],
    max_peer_count: int,
) -> list[PeerMetricRow]:

    candidates = [row for row in rows if row.stock_code != target.stock_code]

    if target.market_cap is not None:
        lo = target.market_cap * _MARKET_CAP_BAND_LOW
        hi = target.market_cap * _MARKET_CAP_BAND_HIGH
        within_band = [
            row for row in candidates
            if row.market_cap is None or lo <= row.market_cap <= hi
        ]
        if len(within_band) >= 2:
            candidates = within_band

    def sort_key(row: PeerMetricRow) -> tuple[int, float]:
        if target.market_cap and row.market_cap:
            gap = abs(row.market_cap - target.market_cap) / target.market_cap
        else:
            gap = 9_999.0
        return (-row.data_quality_score, gap)

    return sorted(candidates, key=sort_key)[:max_peer_count]


def build_peer_summary(
    target: PeerMetricRow,
    peer_count: int,
    data_quality_flags: list[str],
) -> str:
    flag_messages = _dedupe(
        [
            PEER_SUMMARY_FLAG_MESSAGES.get(flag, UNKNOWN_PEER_SUMMARY_FLAG_MESSAGE)
            for flag in data_quality_flags
        ]
    )
    flag_summary = " ".join(flag_messages) if flag_messages else "없음"
    return (
        f"{target.corp_name}은 같은 섹터 peer {peer_count}개와 비교되었습니다. "
        f"데이터 품질 경고: {flag_summary}."
    )


def metric_definitions() -> dict[str, str]:
    return {
        "per": (
            "시가총액을 당기순이익으로 나눈 값입니다. "
            "낮을수록 이익 대비 가격 부담이 작습니다."
        ),
        "pbr": (
            "시가총액을 자본총계로 나눈 값입니다. "
            "낮을수록 장부가치 대비 가격 부담이 작습니다."
        ),
        "roe": "당기순이익을 자본총계로 나눈 수익성 지표입니다. 높을수록 자본 효율이 좋습니다.",
        "revenue_growth": "최근 연도 매출액이 전년 대비 얼마나 증가했는지 나타냅니다.",
        "operating_margin": "영업이익을 매출액으로 나눈 본업 수익성 지표입니다.",
        "debt_ratio": "부채총계를 자본총계로 나눈 재무 안정성 지표입니다. 낮을수록 안정적입니다.",
        "score": (
            "밸류에이션, 수익성, 성장성, 마진, 재무 안정성, 데이터 완성도를 "
            "종합한 0~100점 점수입니다."
        ),
    }


def _dedupe(items: list[str]) -> list[str]:
    deduped: list[str] = []
    for item in items:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _missing_target_row(stock_code: str) -> PeerMetricRow:
    return PeerMetricRow(
        corp_code="",
        stock_code=stock_code,
        corp_name=stock_code,
        data_quality_score=0,
        metric_flags=["target_not_found"],
    )


def build_peer_comparison(
    conn: Connection,
    stock_code: str,
    sector: str | None = None,
    min_peer_count: int = 3,
    max_peer_count: int = 8,
    lookback_years: int = 3,
) -> PeerComparison:
    warnings: list[str] = []
    target_company = load_target_company(conn, stock_code)

    if target_company is None:
        message = f"{stock_code} 종목을 company 테이블에서 찾지 못했습니다."
        flags = ["target_not_found"]
        return PeerComparison(
            target=_missing_target_row(stock_code),
            peers=[],
            score=0,
            peer_selection_summary=message,
            peer_summary=message,
            metric_definitions=metric_definitions(),
            relative_position={},
            evidence=[message],
            data_quality_flags=flags,
            warnings=flags.copy(),
        )

    if not target_company.sector and sector:
        target_company = target_company.model_copy(update={"sector": sector})

    if not target_company.sector:
        warnings.append("sector_missing")
        peer_candidates: list[CompanyPeer] = []
    else:
        peer_candidates = load_peer_candidates(
            conn,
            target_company,
            max_peer_count=max_peer_count,
        )

    companies = [target_company, *peer_candidates]
    stock_codes = [company.stock_code for company in companies]
    corp_codes = [company.corp_code for company in companies]
    prices = load_latest_prices(conn, stock_codes)
    financials = load_financial_snapshots(conn, corp_codes, lookback_years=lookback_years)

    metric_rows: list[PeerMetricRow] = []
    for company in companies:
        latest, previous = financials.get(company.corp_code, (None, None))
        metric_rows.append(
            calculate_metric_row(
                company=company,
                price=prices.get(company.stock_code),
                latest=latest,
                previous=previous,
            )
        )

    target_row = metric_rows[0]

    metric_rows = _mark_outliers(metric_rows, target_row.stock_code)
    target_row = metric_rows[0]
    selected_peers = select_peer_rows(target_row, metric_rows, max_peer_count=max_peer_count)

    if len(selected_peers) < min_peer_count:
        warnings.append("peer_count_below_minimum")

    position = calculate_relative_position([target_row, *selected_peers], target_row.stock_code)
    warnings = _dedupe(warnings)
    data_quality_flags = _dedupe([*position.data_quality_flags, *warnings])

    if target_company.sector:
        peer_selection_summary = (
            f"{target_company.sector} 섹터에서 후보 {len(peer_candidates)}개를 불러와 "
            f"데이터 완성도와 시가총액 근접도 기준으로 {len(selected_peers)}개를 선택했습니다."
        )
    else:
        peer_selection_summary = "섹터 정보가 없어 같은 섹터 peer 후보를 선택하지 못했습니다."

    evidence = [
        *position.evidence,
        f"비교군은 최종 {len(selected_peers)}개 peer로 구성했습니다.",
    ]

    return PeerComparison(
        target=target_row,
        peers=selected_peers,
        score=position.score,
        peer_selection_summary=peer_selection_summary,
        peer_summary=build_peer_summary(target_row, len(selected_peers), data_quality_flags),
        metric_definitions=metric_definitions(),
        relative_position=position.relative_position,
        evidence=evidence,
        data_quality_flags=data_quality_flags,
        a1_peer_multiple_payload=position.a1_peer_multiple_payload,
        warnings=warnings,
    )