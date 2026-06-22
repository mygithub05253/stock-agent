from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from stock_agent.config import get_settings
from stock_agent.llm.glm_client import ChatMessage, GLMClientError, chat_completion_json
from stock_agent.llm.openrouter_client import (
    ChatMessage as OpenRouterChatMessage,
    OpenRouterClientError,
    openrouter_chat_json,
)
from stock_agent.schemas.analysis import AgentState, StrategistResult, InvestmentReport


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
            f"macro: {state.macro.model_dump(mode='json') if state.macro else None}",
            f"current_strategist: {state.strategist.model_dump(mode='json') if state.strategist else None}",
        ]
    )


def _merge_strategist_result(
    current: StrategistResult,
    parsed: dict[str, Any],
    *,
    model_provider: str,
    model: str,
    fallback_used: bool,
) -> StrategistResult:
    payload = current.model_dump(mode="json")
    payload.update(parsed)
    payload.update(
        {
            "model_provider": model_provider,
            "model": model,
            "fallback_used": fallback_used,
        }
    )
    return StrategistResult(**payload)


def run_investment_analyst(state: AgentState) -> AgentState:
    if state.strategist is None:
        raise ValueError("strategist result is required before investment analyst")

    settings = get_settings()
    llm_errors: list[str] = []

    if settings.openrouter_api_key:
        try:
            parsed = openrouter_chat_json(
                [
                    OpenRouterChatMessage(role="system", content=_load_system_prompt()),
                    OpenRouterChatMessage(role="user", content=_analysis_context(state)),
                ],
                max_tokens=900,
            )
            state.strategist = _merge_strategist_result(
                state.strategist,
                parsed,
                model_provider="openrouter",
                model=settings.openrouter_model,
                fallback_used=False,
            )
            # Try to populate InvestmentReport if LLM returned extended fields
            try:
                inv_payload = {}
                if parsed.get("executive_summary"):
                    inv_payload["executive_summary"] = parsed.get("executive_summary")
                if parsed.get("investment_thesis"):
                    inv_payload["thesis"] = parsed.get("investment_thesis")
                if parsed.get("valuation"):
                    inv_payload["valuation"] = parsed.get("valuation")
                if parsed.get("risk_analysis"):
                    inv_payload["risk_analysis"] = parsed.get("risk_analysis")
                if parsed.get("action_plan"):
                    inv_payload["action_plan"] = parsed.get("action_plan")
                if inv_payload:
                    state.investment_report = InvestmentReport(**inv_payload)
            except ValidationError:
                # ignore if report schema doesn't match
                pass
            return state
        except (OpenRouterClientError, ValidationError, OSError, ValueError) as exc:
            llm_errors.append(f"OpenRouter Qwen 호출 실패: {exc}")

    if not settings.glm_api_key:
        state.strategist = state.strategist.model_copy(
            update={
                "model_provider": state.strategist.model_provider or "strategist",
                "model": state.strategist.model or "local-rule",
                "fallback_used": True,
                "risks": [*state.strategist.risks, *llm_errors],
            }
        )
        return state

    try:
        parsed = chat_completion_json(
            [
                ChatMessage(role="system", content=_load_system_prompt()),
                ChatMessage(role="user", content=_analysis_context(state)),
            ]
        )
        state.strategist = _merge_strategist_result(
            state.strategist,
            parsed,
            model_provider="glm",
            model=settings.glm_model,
            fallback_used=bool(llm_errors or not settings.openrouter_api_key),
        )
        # Try to populate InvestmentReport from GLM parsed output as well
        try:
            inv_payload = {}
            if parsed.get("executive_summary"):
                inv_payload["executive_summary"] = parsed.get("executive_summary")
            if parsed.get("investment_thesis"):
                inv_payload["thesis"] = parsed.get("investment_thesis")
            if parsed.get("valuation"):
                inv_payload["valuation"] = parsed.get("valuation")
            if parsed.get("risk_analysis"):
                inv_payload["risk_analysis"] = parsed.get("risk_analysis")
            if parsed.get("action_plan"):
                inv_payload["action_plan"] = parsed.get("action_plan")
            if inv_payload:
                state.investment_report = InvestmentReport(**inv_payload)
        except ValidationError:
            pass
    except (GLMClientError, ValidationError, OSError, ValueError) as exc:
        state.strategist = state.strategist.model_copy(
            update={
                "fallback_used": True,
                "risks": [
                    *state.strategist.risks,
                    *llm_errors,
                    f"GLM 투자 분석기 호출 실패로 mock Strategist 결과를 사용했습니다: {exc}",
                ]
            }
        )
    return state
