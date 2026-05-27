from __future__ import annotations

import re
from dataclasses import dataclass

from stock_agent.schemas import Holding, Portfolio


STOCK_CATALOG = {
    "삼성전자": {"stock_code": "005930", "sector": "반도체", "current_price": 78000},
    "SK하이닉스": {"stock_code": "000660", "sector": "반도체", "current_price": 201000},
    "하이닉스": {"stock_code": "000660", "corp_name": "SK하이닉스", "sector": "반도체", "current_price": 201000},
    "KB금융": {"stock_code": "105560", "sector": "금융", "current_price": 82000},
    "신한지주": {"stock_code": "055550", "sector": "금융", "current_price": 56000},
}


@dataclass(frozen=True)
class HoldingParseResult:
    holdings: list[Holding]
    warnings: list[str]


def parse_holdings_text(text: str) -> HoldingParseResult:
    holdings: list[Holding] = []
    warnings: list[str] = []
    seen_codes: set[str] = set()

    for raw_item in re.split(r"[,，\n]+", text):
        item = raw_item.strip()
        if not item:
            continue

        matched_name = None
        matched_meta = None
        for name, meta in STOCK_CATALOG.items():
            if name.lower() in item.lower():
                matched_name = meta.get("corp_name", name)
                matched_meta = meta
                break

        qty_match = re.search(r"(\d+)\s*주", item)
        if matched_name is None or matched_meta is None or qty_match is None:
            warnings.append(f"해석하지 못한 보유 종목 입력: {item}")
            continue

        stock_code = str(matched_meta["stock_code"])
        if stock_code in seen_codes:
            warnings.append(f"중복 종목은 한 번만 반영했습니다: {matched_name}")
            continue
        seen_codes.add(stock_code)

        qty = int(qty_match.group(1))
        current_price = int(matched_meta["current_price"])
        holdings.append(
            Holding(
                stock_code=stock_code,
                corp_name=matched_name,
                sector=str(matched_meta["sector"]),
                avg_price=current_price,
                qty=qty,
                current_price=current_price,
            )
        )

    return HoldingParseResult(holdings=build_holding_weights(holdings), warnings=warnings)


def build_holding_weights(holdings: list[Holding]) -> list[Holding]:
    total_value = sum(holding.market_value or 0 for holding in holdings)
    if total_value <= 0:
        return holdings
    return [
        holding.model_copy(update={"weight": (holding.market_value or 0) / total_value})
        for holding in holdings
    ]


def build_portfolio_from_text(text: str, cash_weight: float = 0.2) -> tuple[Portfolio, list[str]]:
    result = parse_holdings_text(text)
    return Portfolio(holdings=result.holdings, cash_weight=cash_weight), result.warnings
