from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import re

from stock_agent.agents.investor_profile import run_investor_profile_agent
from stock_agent.schemas import Holding, Portfolio, UserProfile


STOCK_CATALOG = {
    "SK하이닉스": {
        "stock_code": "000660",
        "sector": "반도체",
        "current_price": 201000,
        "market_cap_rank": 1,
    },
    "삼성전자": {
        "stock_code": "005930",
        "sector": "반도체",
        "current_price": 78000,
        "market_cap_rank": 2,
    },
    "한미반도체": {
        "stock_code": "042700",
        "sector": "반도체",
        "current_price": 145000,
        "market_cap_rank": 3,
    },
    "리노공업": {
        "stock_code": "058470",
        "sector": "반도체",
        "current_price": 225000,
        "market_cap_rank": 4,
    },
    "이오테크닉스": {
        "stock_code": "039030",
        "sector": "반도체",
        "current_price": 175000,
        "market_cap_rank": 5,
    },
    "DB하이텍": {
        "stock_code": "000990",
        "sector": "반도체",
        "current_price": 52000,
        "market_cap_rank": 6,
    },
    "HPSP": {
        "stock_code": "403870",
        "sector": "반도체",
        "current_price": 43200,
        "market_cap_rank": 7,
    },
    "ISC": {
        "stock_code": "095340",
        "sector": "반도체",
        "current_price": 78000,
        "market_cap_rank": 8,
    },
    "이수페타시스": {
        "stock_code": "007660",
        "sector": "반도체",
        "current_price": 48000,
        "market_cap_rank": 9,
    },
    "하나마이크론": {
        "stock_code": "067310",
        "sector": "반도체",
        "current_price": 26000,
        "market_cap_rank": 10,
    },
    "KB금융": {
        "stock_code": "105560",
        "sector": "금융",
        "current_price": 82000,
        "market_cap_rank": 1,
    },
    "신한지주": {
        "stock_code": "055550",
        "sector": "금융",
        "current_price": 56000,
        "market_cap_rank": 2,
    },
    "하나금융지주": {
        "stock_code": "086790",
        "sector": "금융",
        "current_price": 68000,
        "market_cap_rank": 3,
    },
    "우리금융지주": {
        "stock_code": "316140",
        "sector": "금융",
        "current_price": 16500,
        "market_cap_rank": 4,
    },
    "기업은행": {
        "stock_code": "024110",
        "sector": "금융",
        "current_price": 15500,
        "market_cap_rank": 5,
    },
    "카카오뱅크": {
        "stock_code": "323410",
        "sector": "금융",
        "current_price": 24000,
        "market_cap_rank": 6,
    },
    "한국금융지주": {
        "stock_code": "071050",
        "sector": "금융",
        "current_price": 83000,
        "market_cap_rank": 7,
    },
    "BNK금융지주": {
        "stock_code": "138930",
        "sector": "금융",
        "current_price": 10500,
        "market_cap_rank": 8,
    },
    "JB금융지주": {
        "stock_code": "175330",
        "sector": "금융",
        "current_price": 16500,
        "market_cap_rank": 9,
    },
    "iM금융지주": {
        "stock_code": "139130",
        "sector": "금융",
        "current_price": 10500,
        "market_cap_rank": 10,
    },
    "하이닉스": {
        "stock_code": "000660",
        "corp_name": "SK하이닉스",
        "sector": "반도체",
        "current_price": 201000,
        "market_cap_rank": 1,
    },
}


def get_stock_options(preferred_sectors: list[str] | None = None, limit: int = 10) -> list[str]:
    sectors = preferred_sectors or ["반도체", "금융"]
    canonical_items = [
        (name, meta)
        for name, meta in STOCK_CATALOG.items()
        if "corp_name" not in meta and meta["sector"] in sectors
    ]

    if len(sectors) >= 2:
        per_sector_limit = max(1, limit // len(sectors))
        options: list[str] = []
        for sector in sectors:
            sector_items = sorted(
                [item for item in canonical_items if item[1]["sector"] == sector],
                key=lambda item: int(item[1].get("market_cap_rank", 999)),
            )
            options.extend(name for name, _ in sector_items[:per_sector_limit])
        if len(options) < limit:
            remaining = sorted(
                [item for item in canonical_items if item[0] not in options],
                key=lambda item: (str(item[1]["sector"]), int(item[1].get("market_cap_rank", 999))),
            )
            options.extend(name for name, _ in remaining[: limit - len(options)])
        return options[:limit]

    return [
        name
        for name, _ in sorted(
            canonical_items,
            key=lambda item: int(item[1].get("market_cap_rank", 999)),
        )[:limit]
    ]


@dataclass(frozen=True)
class HoldingParseResult:
    holdings: list[Holding]
    warnings: list[str]


ONBOARDING_CARDS = [
    {
        "id": "investment_goal",
        "question": "투자 목적은 무엇인가요?",
        "options": [
            {"label": "안정적 자산관리", "value": "wealth_preservation", "score": 0},
            {"label": "중장기 성장", "value": "growth", "score": 1},
            {"label": "단기 수익", "value": "short_term_profit", "score": 2},
            {"label": "배당", "value": "dividend", "score": 0},
        ],
    },
    {
        "id": "investment_horizon_months",
        "question": "투자 기간은 어느 정도로 생각하시나요?",
        "options": [
            {"label": "3개월 이하", "value": 3, "score": 0},
            {"label": "6~12개월", "value": 12, "score": 1},
            {"label": "1~3년", "value": 24, "score": 1},
            {"label": "3년 이상", "value": 36, "score": 2},
        ],
    },
    {
        "id": "max_drawdown_tolerance",
        "question": "감내 가능한 손실 폭은 어느 정도인가요?",
        "options": [
            {"label": "-5% 이내", "value": -0.05, "score": 0},
            {"label": "-10% 이내", "value": -0.1, "score": 1},
            {"label": "-20% 이내", "value": -0.2, "score": 2},
            {"label": "-30% 이상도 감내", "value": -0.3, "score": 2},
        ],
    },
    {
        "id": "loss_reaction",
        "question": "보유 종목이 한 달에 -10% 하락하면 어떻게 하시겠어요?",
        "options": [
            {"label": "비중을 줄인다", "value": "reduce", "score": 0},
            {"label": "일단 기다린다", "value": "hold", "score": 1},
            {"label": "추가 매수도 고려한다", "value": "buy_more", "score": 2},
        ],
    },
    {
        "id": "liquidity_need_level",
        "question": "이 투자금은 얼마나 빨리 필요할 수 있나요?",
        "options": [
            {"label": "곧 필요할 수 있다", "value": "high", "score": 0},
            {"label": "일부 필요할 수 있다", "value": "medium", "score": 1},
            {"label": "여유자금이다", "value": "low", "score": 2},
        ],
    },
    {
        "id": "experience_level",
        "question": "투자 경험은 어느 정도인가요?",
        "options": [
            {"label": "처음 또는 초보", "value": "beginner", "score": 0},
            {"label": "몇 번 해봤다", "value": "intermediate", "score": 1},
            {"label": "직접 종목 분석 가능", "value": "advanced", "score": 2},
        ],
    },
    {
        "id": "preferred_sectors",
        "question": "관심 산업은 어디인가요?",
        "options": [
            {"label": "반도체", "value": ["반도체"], "score": 1},
            {"label": "금융", "value": ["금융"], "score": 1},
            {"label": "둘 다", "value": ["반도체", "금융"], "score": 1},
        ],
    },
]


def get_onboarding_card(card_index: int) -> dict[str, Any]:
    return ONBOARDING_CARDS[card_index]


def onboarding_card_count() -> int:
    return len(ONBOARDING_CARDS)


def infer_user_profile(answers: dict[str, Any], user_id: str = "session-user") -> UserProfile:
    return run_investor_profile_agent(answers, user_id=user_id)


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


def build_holding_weights(
    holdings: list[Holding],
    *,
    total_assets: int | float | None = None,
) -> list[Holding]:
    denominator = total_assets
    if denominator is None:
        denominator = sum(holding.market_value or 0 for holding in holdings)
    if denominator <= 0:
        return holdings
    return [
        holding.model_copy(update={"weight": (holding.market_value or 0) / denominator})
        for holding in holdings
    ]


def build_holding_from_selection(corp_name: str, qty: int, avg_price: int | None = None) -> Holding:
    meta = STOCK_CATALOG[corp_name]
    current_price = int(meta["current_price"])
    return Holding(
        stock_code=str(meta["stock_code"]),
        corp_name=str(meta.get("corp_name", corp_name)),
        sector=str(meta["sector"]),
        avg_price=avg_price if avg_price is not None else current_price,
        qty=qty,
        current_price=current_price,
    )


def build_portfolio_from_holdings(holdings: list[Holding], cash_amount: int) -> Portfolio:
    holdings_value = sum(holding.market_value or 0 for holding in holdings)
    total_assets = holdings_value + cash_amount
    cash_weight = cash_amount / total_assets if total_assets > 0 else 0
    return Portfolio(
        holdings=build_holding_weights(holdings, total_assets=total_assets),
        cash_weight=cash_weight,
    )


def build_portfolio_from_text(text: str, cash_weight: float = 0.2) -> tuple[Portfolio, list[str]]:
    result = parse_holdings_text(text)
    return Portfolio(holdings=result.holdings, cash_weight=cash_weight), result.warnings
