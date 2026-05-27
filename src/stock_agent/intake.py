from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from stock_agent.schemas import Holding, Portfolio, UserProfile


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


def _score_answers(answers: dict[str, Any]) -> int:
    score = 0
    for card in ONBOARDING_CARDS:
        selected = answers.get(card["id"])
        for option in card["options"]:
            if option["value"] == selected:
                score += int(option["score"])
                break
    return score


def infer_user_profile(answers: dict[str, Any], user_id: str = "session-user") -> UserProfile:
    score = _score_answers(answers)
    risk_tolerance = "low" if score <= 5 else "medium" if score <= 9 else "high"

    horizon = int(answers.get("investment_horizon_months", 12))
    drawdown = float(answers.get("max_drawdown_tolerance", -0.1))
    liquidity = str(answers.get("liquidity_need_level", "medium"))

    if drawdown >= -0.05 and liquidity == "high":
        risk_tolerance = "low"
    elif horizon <= 3 and risk_tolerance == "high":
        risk_tolerance = "medium"

    target_return_rate = 0.05 if risk_tolerance == "low" else 0.1 if risk_tolerance == "medium" else 0.2

    return UserProfile(
        user_id=user_id,
        risk_tolerance=risk_tolerance,
        investment_horizon_months=horizon,
        target_return_rate=target_return_rate,
        max_drawdown_tolerance=drawdown,
        investment_goal=answers.get("investment_goal", "growth"),
        experience_level=answers.get("experience_level", "beginner"),
        preferred_sectors=answers.get("preferred_sectors", ["반도체"]),
        liquidity_need_level=liquidity,
    )


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


def build_holding_from_selection(corp_name: str, qty: int) -> Holding:
    meta = STOCK_CATALOG[corp_name]
    current_price = int(meta["current_price"])
    return Holding(
        stock_code=str(meta["stock_code"]),
        corp_name=str(meta.get("corp_name", corp_name)),
        sector=str(meta["sector"]),
        avg_price=current_price,
        qty=qty,
        current_price=current_price,
    )


def build_portfolio_from_text(text: str, cash_weight: float = 0.2) -> tuple[Portfolio, list[str]]:
    result = parse_holdings_text(text)
    return Portfolio(holdings=result.holdings, cash_weight=cash_weight), result.warnings
