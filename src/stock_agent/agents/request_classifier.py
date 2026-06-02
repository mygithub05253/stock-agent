from pathlib import Path

from stock_agent.config import get_settings
from stock_agent.llm.glm_client import ChatMessage, GLMClientError, chat_completion_json
from stock_agent.schemas.analysis import AgentState


_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "request_classifier" / "system.md"


def _load_system_prompt() -> str:
    try:
        return _PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return (
            "You are a request classifier for a Korean stock analysis app. "
            "Return only JSON with intent, target_stock_code, target_corp_name, target_sector, "
            "analysis_scope, urgency_reason, and requested_depth."
        )


def _detect_urgency_reason(query: str) -> str:
    if any(keyword in query for keyword in ("급등", "상승", "올랐")):
        return "surge"
    if any(keyword in query for keyword in ("급락", "하락", "떨어졌", "빠졌")):
        return "drop"
    if any(keyword in query for keyword in ("실적", "어닝", "발표")):
        return "earnings"
    if any(keyword in query for keyword in ("뉴스", "공시", "이슈")):
        return "news"
    return "general"


def _classify_request_intent(query: str, curator_intent: str) -> str:
    if curator_intent == "포트폴리오 전체 점검":
        return "portfolio_review"
    if any(keyword in query for keyword in ("팔", "매도", "익절", "손절", "정리")):
        return "sell_decision"
    if any(keyword in query for keyword in ("위험", "리스크", "괜찮", "비중", "손실")):
        return "risk_review"
    if curator_intent == "신규 관심 종목 점검":
        return "new_recommendation"
    return "holding_review"


def _detect_sector(query: str, curator_sector: str | None, preferred_sectors: list[str]) -> str | None:
    if "반도체" in query:
        return "반도체"
    if any(keyword in query for keyword in ("금융", "은행", "증권")):
        return "금융"
    if curator_sector and curator_sector != "미분류":
        return curator_sector
    if preferred_sectors:
        return preferred_sectors[0]
    return None


def _detect_analysis_scope(query: str, curator_intent: str) -> str:
    if any(keyword in query for keyword in ("업황", "산업", "산업분석", "업종", "섹터")):
        return "sector"
    if curator_intent == "포트폴리오 전체 점검":
        return "portfolio"
    return "single_stock"


def _build_default_request(state: AgentState, query: str) -> dict[str, str | None]:
    analysis_scope = _detect_analysis_scope(query, state.curator.intent)
    target_sector = _detect_sector(query, state.curator.sector, state.user_profile.preferred_sectors)
    return {
        "intent": _classify_request_intent(query, state.curator.intent),
        "target_stock_code": state.curator.stock_code,
        "target_corp_name": state.curator.corp_name,
        "target_sector": target_sector,
        "analysis_scope": analysis_scope,
        "urgency_reason": _detect_urgency_reason(query),
        "requested_depth": state.user_request.requested_depth if state.user_request else "summary",
    }


def _apply_glm_request_classification(state: AgentState, query: str) -> dict[str, str | None]:
    settings = get_settings()
    if not settings.glm_api_key:
        return _build_default_request(state, query)

    try:
        parsed = chat_completion_json(
            [
                ChatMessage(role="system", content=_load_system_prompt()),
                ChatMessage(
                    role="user",
                    content=(
                        f"user_query: {state.user_request.raw_query if state.user_request else query}\n"
                        f"user_profile: {state.user_profile.model_dump(mode='json')}\n"
                        f"curator: {state.curator.model_dump(mode='json') if state.curator else None}\n"
                        f"portfolio_holdings: {[holding.model_dump(mode='json') for holding in state.portfolio.holdings]}\n"
                    ),
                ),
            ],
            temperature=0.0,
        )
    except (GLMClientError, OSError, ValueError):
        return _build_default_request(state, query)

    defaults = _build_default_request(state, query)
    for key in defaults:
        value = parsed.get(key)
        if value not in (None, ""):
            defaults[key] = value

    if defaults["analysis_scope"] == "portfolio":
        defaults["target_stock_code"] = defaults.get("target_stock_code") or state.curator.stock_code
        defaults["target_corp_name"] = defaults.get("target_corp_name") or state.curator.corp_name

    if defaults.get("target_sector") is None:
        defaults["target_sector"] = _detect_sector(query, state.curator.sector, state.user_profile.preferred_sectors)

    return defaults


def run_request_classifier(state: AgentState) -> AgentState:
    if state.user_request is None:
        return state
    if state.curator is None:
        raise ValueError("curator result is required before request classification")

    query = state.user_request.raw_query.lower()
    classified = _apply_glm_request_classification(state, query)
    state.user_request = state.user_request.model_copy(
        update={
            "intent": classified["intent"],
            "target_stock_code": classified["target_stock_code"],
            "target_corp_name": classified["target_corp_name"],
            "target_sector": classified["target_sector"],
            "analysis_scope": classified["analysis_scope"],
            "urgency_reason": classified["urgency_reason"],
            "requested_depth": classified["requested_depth"],
        }
    )
    return state