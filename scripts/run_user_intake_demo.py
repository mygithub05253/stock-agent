from __future__ import annotations

import argparse
import json
from typing import Any

from stock_agent.graph import build_demo_profile, run_phase1_analysis
from stock_agent.schemas import Holding, Portfolio, UserProfile


DEFAULT_QUERIES = [
    "내 포트폴리오에서 삼성전자 어떻게 할까?",
    "SK하이닉스 비중 괜찮아?",
    "요즘 내 포트폴리오에서 볼만한 종목 알려줘",
]


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _build_conservative_surge_context() -> tuple[UserProfile, Portfolio]:
    return (
        UserProfile(
            user_id="demo-conservative",
            risk_tolerance="low",
            investment_horizon_months=3,
            target_return_rate=0.05,
            max_drawdown_tolerance=-0.05,
            investment_goal="wealth_preservation",
            experience_level="beginner",
            preferred_sectors=["반도체"],
            liquidity_need_level="high",
        ),
        Portfolio(
            holdings=[
                Holding(
                    stock_code="005930",
                    corp_name="삼성전자",
                    sector="반도체",
                    weight=0.75,
                    avg_price=70000,
                    qty=20,
                    current_price=78000,
                )
            ],
            cash_weight=0.05,
        ),
    )


def _run_case(query: str, profile: UserProfile, portfolio: Portfolio) -> dict[str, Any]:
    output = run_phase1_analysis(query, user_profile=profile, portfolio=portfolio)
    return {
        "input": {
            "query": query,
            "profile": _to_jsonable(profile),
            "portfolio": _to_jsonable(portfolio),
        },
        "user_request": _to_jsonable(output.state.user_request),
        "curator": _to_jsonable(output.state.curator),
        "tier1": _to_jsonable(output.tier1),
        "strategist_next_actions": output.state.strategist.next_actions
        if output.state.strategist
        else [],
        "warnings": {
            "curator": output.state.curator.warnings if output.state.curator else [],
            "guardrail": output.state.guardrail.warnings if output.state.guardrail else [],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the user intake / curator demo and print structured agent output."
    )
    parser.add_argument("--query", help="Run one custom query instead of the default examples.")
    parser.add_argument(
        "--scenario",
        choices=["default", "conservative_surge"],
        default="default",
        help="Demo input context to use.",
    )
    args = parser.parse_args()

    if args.scenario == "conservative_surge":
        profile, portfolio = _build_conservative_surge_context()
        queries = [args.query or "삼성전자 급등했는데 안정형이면 어떻게 할까?"]
    else:
        profile, portfolio = build_demo_profile()
        queries = [args.query] if args.query else DEFAULT_QUERIES

    results = [_run_case(query, profile, portfolio) for query in queries]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
