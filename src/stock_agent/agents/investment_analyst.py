from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from stock_agent.config import get_settings
from stock_agent.llm.glm_client import ChatMessage, GLMClientError, chat_completion_json
from stock_agent.schemas.analysis import AgentState, StrategistResult


_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "investment_analyst" / "system.md"


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _holding_payload(state: AgentState) -> list[dict[str, Any]]:
    return [
        {
            "corp_name": holding.corp_name,
            "stock_code": holding.stock_code,
            "sector": holding.sector,
            "qty": holding.qty,
            "avg_price": holding.avg_price,
            "current_price": holding.current_price,
            "cost_basis": holding.cost_basis,
            "market_value": holding.market_value,
            "weight": holding.weight,
        }
        for holding in state.portfolio.holdings
    ]


def _analysis_context(state: AgentState) -> str:
    return "\n".join(
        [
            f"user_query: {state.user_query}",
            f"user_profile: {state.user_profile.model_dump(mode='json')}",
            f"portfolio: cash_weight={state.portfolio.cash_weight}, holdings={_holding_payload(state)}",
            f"user_request: {state.user_request.model_dump(mode='json') if state.user_request else None}",
            f"curator: {state.curator.model_dump(mode='json') if state.curator else None}",
            f"quant: {state.quant.model_dump(mode='json') if state.quant else None}",
            f"qual: {state.qual.model_dump(mode='json') if state.qual else None}",
            f"competitor: {state.competitor.model_dump(mode='json') if state.competitor else None}",
            f"current_strategist: {state.strategist.model_dump(mode='json') if state.strategist else None}",
        ]
    )


def run_investment_analyst(state: AgentState) -> AgentState:
    if state.strategist is None:
        raise ValueError("strategist result is required before investment analyst")
    if not get_settings().glm_api_key:
        return state

    try:
        parsed = chat_completion_json(
            [
                ChatMessage(role="system", content=_load_system_prompt()),
                ChatMessage(role="user", content=_analysis_context(state)),
            ]
        )
        state.strategist = StrategistResult(**parsed)
    except (GLMClientError, ValidationError, OSError, ValueError) as exc:
        state.strategist = state.strategist.model_copy(
            update={
                "risks": [
                    *state.strategist.risks,
                    f"GLM 투자 분석기 호출 실패로 mock Strategist 결과를 사용했습니다: {exc}",
                ]
            }
        )
    return state
