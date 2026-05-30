from typing import Any

from stock_agent.schemas import UserProfile


_ANSWER_SCORES = {
    "investment_goal": {
        "wealth_preservation": 0,
        "growth": 1,
        "short_term_profit": 2,
        "dividend": 0,
    },
    "investment_horizon_months": {3: 0, 12: 1, 24: 1, 36: 2},
    "max_drawdown_tolerance": {-0.05: 0, -0.1: 1, -0.2: 2, -0.3: 2},
    "loss_reaction": {"reduce": 0, "hold": 1, "buy_more": 2},
    "liquidity_need_level": {"high": 0, "medium": 1, "low": 2},
    "experience_level": {"beginner": 0, "intermediate": 1, "advanced": 2},
    "preferred_sectors": {
        ("반도체",): 1,
        ("금융",): 1,
        ("반도체", "금융"): 1,
    },
}


def _score_answers(answers: dict[str, Any]) -> int:
    score = 0
    for answer_id, score_map in _ANSWER_SCORES.items():
        selected = answers.get(answer_id)
        if isinstance(selected, list):
            selected = tuple(selected)
        score += int(score_map.get(selected, 0))
    return score


def run_investor_profile_agent(answers: dict[str, Any], user_id: str = "session-user") -> UserProfile:
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
