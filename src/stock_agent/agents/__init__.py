from importlib import import_module
from typing import Any


_EXPORTS = {
    "run_competitor": "stock_agent.agents.competitor",
    "run_curator": "stock_agent.agents.curator",
    "run_guardrail": "stock_agent.agents.guardrail",
    "run_investment_analyst": "stock_agent.agents.investment_analyst",
    "run_investor_profile_agent": "stock_agent.agents.investor_profile",
    "run_qual": "stock_agent.agents.qual",
    "run_quant": "stock_agent.agents.quant",
    "run_macro": "stock_agent.agents.macro",
    "run_request_classifier": "stock_agent.agents.request_classifier",
    "run_strategist": "stock_agent.agents.strategist",
    "run_result_renderer": "stock_agent.agents.result_renderer",
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(_EXPORTS[name])
    value = getattr(module, name)
    globals()[name] = value
    return value


__all__ = [
    "run_competitor",
    "run_curator",
    "run_guardrail",
    "run_investment_analyst",
    "run_investor_profile_agent",
    "run_qual",
    "run_quant",
    "run_macro",
    "run_request_classifier",
    "run_strategist",
    "run_result_renderer",
]
