from pathlib import Path

from stock_agent.config import get_settings
from stock_agent.llm.glm_client import ChatMessage, GLMClientError, chat_completion_json
from stock_agent.schemas.analysis import AgentState, CuratorResult


_MVP_SECTORS = {"반도체", "금융"}
_COMPANY_ALIASES = {
    "삼성전자": {
        "corp_name": "삼성전자",
        "stock_code": "005930",
        "corp_code": "00126380",
        "sector": "반도체",
    },
    "samsung": {
        "corp_name": "삼성전자",
        "stock_code": "005930",
        "corp_code": "00126380",
        "sector": "반도체",
    },
    "sk하이닉스": {
        "corp_name": "SK하이닉스",
        "stock_code": "000660",
        "corp_code": "00164779",
        "sector": "반도체",
    },
    "하이닉스": {
        "corp_name": "SK하이닉스",
        "stock_code": "000660",
        "corp_code": "00164779",
        "sector": "반도체",
    },
    "kb금융": {
        "corp_name": "KB금융",
        "stock_code": "105560",
        "corp_code": "00688996",
        "sector": "금융",
    },
    "신한지주": {
        "corp_name": "신한지주",
        "stock_code": "055550",
        "corp_code": "00382199",
        "sector": "금융",
    },
}

# Curator 설계 원칙: KRX 종목코드와 DART corp_code를 "함께" 반환해야 한다.
# GLM 응답이나 보유종목 경로에서 corp_code가 비면 Quant/Qual의 DART 재무 조회가
# 전부 실패하므로, 알려진 종목은 카탈로그에서 corp_code를 보충한다.
_STOCK_TO_CORP = {
    alias["stock_code"]: alias["corp_code"]
    for alias in _COMPANY_ALIASES.values()
    if alias.get("corp_code")
}


def _resolve_corp_code(stock_code: str | None, corp_code: str | None) -> str | None:
    if corp_code:
        return corp_code
    if stock_code:
        return _STOCK_TO_CORP.get(stock_code)
    return None


def run_curator(state: AgentState) -> AgentState:
    query = (state.user_request.raw_query if state.user_request else state.user_query).lower()
    # If a GLM key is configured, attempt to ask the GLM for a suggested selection first.
    try:
        settings = get_settings()
        if settings.glm_api_key:
            # load system prompt if present
            prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "curator" / "system.md"
            try:
                system_prompt = prompt_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                system_prompt = (
                    "You are a curator assistant. Given the user query, user profile and portfolio, "
                    "return a JSON object with keys: corp_name, stock_code, corp_code (nullable), sector, intent, "
                    "candidates (list), warnings (list)."
                )

            # build user context
            holdings = [
                {
                    "corp_name": h.corp_name,
                    "stock_code": h.stock_code,
                    "sector": h.sector,
                    "weight": h.weight,
                }
                for h in state.portfolio.holdings
            ]
            user_message = (
                f"user_query: {state.user_request.raw_query if state.user_request else state.user_query}\n"
                f"user_profile: {state.user_profile.model_dump(mode='json')}\n"
                f"portfolio_holdings: {holdings}\n"
            )

            try:
                parsed = chat_completion_json(
                    [
                        ChatMessage(role="system", content=system_prompt),
                        ChatMessage(role="user", content=user_message),
                    ],
                    temperature=0.0,
                )
                # expect parsed to be a dict with selection keys
                if isinstance(parsed, dict) and parsed.get("stock_code") and parsed.get("corp_name"):
                    selected = {
                        "corp_name": parsed.get("corp_name"),
                        "stock_code": parsed.get("stock_code"),
                        "corp_code": parsed.get("corp_code"),
                        "sector": parsed.get("sector") or "미분류",
                    }
                    candidates = parsed.get("candidates", [])
                    warnings = parsed.get("warnings", [])
                    intent = parsed.get("intent", "신규 관심 종목 점검")

                    state.curator = CuratorResult(
                        intent=intent,
                        corp_name=selected["corp_name"],
                        stock_code=selected["stock_code"],
                        corp_code=_resolve_corp_code(selected["stock_code"], selected.get("corp_code")),
                        sector=selected["sector"],
                        candidates=list(candidates),
                        warnings=list(warnings),
                    )
                    return state
            except (GLMClientError, Exception):
                # fall back to rule-based selection below on any GLM error
                pass
    except Exception:
        # if settings cannot be loaded for any reason, ignore and proceed with rule base
        pass
    selected = None
    for alias, company in _COMPANY_ALIASES.items():
        if alias.lower() in query or company["stock_code"] in query:
            selected = company
            break

    holding_by_code = {holding.stock_code: holding for holding in state.portfolio.holdings}
    holding_by_name = {holding.corp_name.lower(): holding for holding in state.portfolio.holdings}
    if selected is None:
        for corp_name, holding in holding_by_name.items():
            if corp_name in query or holding.stock_code in query:
                selected = {
                    "corp_name": holding.corp_name,
                    "stock_code": holding.stock_code,
                    "corp_code": None,
                    "sector": holding.sector or "미분류",
                }
                break

    warnings: list[str] = []
    if selected is None:
        preferred_sectors = set(state.user_profile.preferred_sectors)
        candidate_holdings = [
            holding
            for holding in state.portfolio.holdings
            if not preferred_sectors or holding.sector in preferred_sectors
        ]
        if not candidate_holdings:
            candidate_holdings = state.portfolio.holdings

        selected_holding = candidate_holdings[0] if candidate_holdings else None
        if selected_holding is None:
            selected = _COMPANY_ALIASES["삼성전자"]
            candidates = ["삼성전자", "SK하이닉스", "KB금융", "신한지주"]
            warnings.append("보유 종목이 없어 MVP 기본 후보를 반환했습니다.")
        else:
            selected = {
                "corp_name": selected_holding.corp_name,
                "stock_code": selected_holding.stock_code,
                "corp_code": None,
                "sector": selected_holding.sector or "미분류",
            }
            candidates = [holding.corp_name for holding in candidate_holdings]
        intent = "포트폴리오 전체 점검"
    else:
        candidates = []
        is_holding = selected["stock_code"] in holding_by_code
        intent = "보유 종목 판단 지원" if is_holding else "신규 관심 종목 점검"

    if selected["sector"] not in _MVP_SECTORS:
        warnings.append(f"MVP 지원 산업은 반도체/금융 중심입니다: {selected['sector']}")

    state.curator = CuratorResult(
        intent=intent,
        corp_name=selected["corp_name"],
        stock_code=selected["stock_code"],
        corp_code=_resolve_corp_code(selected["stock_code"], selected["corp_code"]),
        sector=selected["sector"],
        candidates=candidates,
        warnings=warnings,
    )
    return state