from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from stock_agent.agents.fallback import should_fallback
from stock_agent.config import get_settings
from stock_agent.llm.openrouter_client import ChatMessage, openrouter_chat_json
from stock_agent.schemas.analysis import AgentState, CompetitorResult
from stock_agent.tools.peer_tool import (
    PeerComparison,
    build_comparison_from_market_rows,
    build_peer_comparison,
)

try:
    from stock_agent.db import get_connection
except ModuleNotFoundError as exc:
    if exc.name != "psycopg":
        raise

    def get_connection():
        raise RuntimeError("psycopg is required to connect to the DB.")



_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "competitor" / "system.md"

_narrative_cache: dict[str, dict[str, Any]] = {}

def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _cache_key(stock_code: str) -> str:
    return f"{stock_code}_{date.today().isoformat()}"


def _comparison_payload(comparison: PeerComparison) -> str:
    data: dict[str, Any] = {
        "target": {
            "corp_name": comparison.target.corp_name,
            "stock_code": comparison.target.stock_code,
            "sector": comparison.target.sector,
            "per": comparison.target.per,
            "pbr": comparison.target.pbr,
            "roe": comparison.target.roe,
            "revenue_growth": comparison.target.revenue_growth,
            "operating_margin": comparison.target.operating_margin,
            "debt_ratio": comparison.target.debt_ratio,
            "data_quality_score": comparison.target.data_quality_score,
        },
        "peers": [
            {
                "corp_name": p.corp_name,
                "per": p.per,
                "pbr": p.pbr,
                "roe": p.roe,
                "revenue_growth": p.revenue_growth,
                "operating_margin": p.operating_margin,
                "debt_ratio": p.debt_ratio,
            }
            for p in comparison.peers
        ],
        "relative_position": comparison.relative_position,
        "score": comparison.score,
        "data_quality_flags": comparison.data_quality_flags,
        "peer_count": len(comparison.peers),
    }
    return json.dumps(data, ensure_ascii=False, default=str)


def _generate_narrative(comparison: PeerComparison) -> dict[str, Any] | None:
    """OpenRouter LLM에서 narrative를 생성한다. key 없음·실패 시 None 반환."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        return None

    key = _cache_key(comparison.target.stock_code)
    if key in _narrative_cache:
        return _narrative_cache[key]

    # 키에 날짜가 들어가므로 날짜가 바뀌면 어제 항목은 다시 조회되지 않는다.
    # 장기 실행 프로세스에서 캐시가 무한히 쌓이지 않도록 오늘 키만 남긴다.
    today_suffix = f"_{date.today().isoformat()}"
    for stale_key in [k for k in _narrative_cache if not k.endswith(today_suffix)]:
        del _narrative_cache[stale_key]

    try:
        result = openrouter_chat_json(
            [
                ChatMessage(role="system", content=_load_system_prompt()),
                ChatMessage(role="user", content=_comparison_payload(comparison)),
            ],
            max_tokens=800,
        )
        _narrative_cache[key] = result
        return result
    except Exception:
        return None


def _apply_narrative(base: CompetitorResult, narrative: dict[str, Any] | None) -> CompetitorResult:
    """LLM narrative를 rule-based CompetitorResult에 merge한다. 수치 필드는 건드리지 않는다."""
    if not narrative:
        return base
    updates: dict[str, Any] = {}
    if isinstance(narrative.get("peer_summary"), str) and narrative["peer_summary"].strip():
        updates["peer_summary"] = narrative["peer_summary"]
    if isinstance(narrative.get("evidence_cards"), list):
        updates["evidence_cards"] = narrative["evidence_cards"]
    if isinstance(narrative.get("bear_case"), str) and narrative["bear_case"].strip():
        updates["bear_case"] = narrative["bear_case"]
    if isinstance(narrative.get("data_gaps"), list):
        extra = [f"data_gap: {g}" for g in narrative["data_gaps"] if g and f"data_gap: {g}" not in base.warnings]
        if extra:
            updates["warnings"] = list(base.warnings) + extra
    return base.model_copy(update=updates) if updates else base


def _peer_row_to_dict(row) -> dict[str, float | int | str | None]:
    return {
        "stock_code": row.stock_code,
        "corp_code": row.corp_code,
        "corp_name": row.corp_name,
        "sector": row.sector,
        "market_cap": row.market_cap,
        "close_price": row.close_price,
        "per": row.per,
        "pbr": row.pbr,
        "roe": row.roe,
        "revenue_growth": row.revenue_growth,
        "operating_margin": row.operating_margin,
        "debt_ratio": row.debt_ratio,
        "data_quality_score": row.data_quality_score,
    }


def _result_from_comparison(comparison: PeerComparison) -> CompetitorResult:
    return CompetitorResult(
        score=comparison.score,
        peer_summary=comparison.peer_summary,
        peers=[_peer_row_to_dict(row) for row in comparison.peers],
        evidence=list(comparison.evidence),
        peer_selection_summary=comparison.peer_selection_summary,
        metric_definitions=dict(comparison.metric_definitions),
        relative_position=dict(comparison.relative_position),
        data_quality_flags=list(comparison.data_quality_flags),
        a1_peer_multiple_payload=(
            dict(comparison.a1_peer_multiple_payload)
            if comparison.a1_peer_multiple_payload is not None
            else None
        ),
        warnings=list(comparison.warnings),
    )


def _mcp_fallback_result(state: AgentState, reason: str) -> CompetitorResult | None:
    """DB 미연결 시 자체 MCP 서버로 pykrx 실시간 시세 기반 peer 비교를 시도한다.

    성공하면 실데이터 기반 CompetitorResult(가능하면 LLM narrative 병합)를 반환하고,
    MCP 미설치·기동 실패·타임아웃·빈 결과면 None을 반환해 상위가 mock으로 폴백하게 한다.
    """
    settings = get_settings()
    if not settings.competitor_mcp_fallback_enabled:
        return None

    try:
        from stock_agent.mcp_bridge.peer_data_client import (
            McpUnavailableError,
            fetch_mcp_peer_data,
        )
    except Exception:
        return None

    try:
        data = fetch_mcp_peer_data(
            stock_code=state.curator.stock_code,
            sector=state.curator.sector,
            timeout=settings.competitor_mcp_timeout_seconds,
        )
    except McpUnavailableError:
        return None
    except Exception:
        # MCP 경로의 예기치 못한 오류는 데모 흐름을 막지 않도록 mock으로 양보한다.
        return None

    if not data.records:
        return None

    comparison = build_comparison_from_market_rows(
        target_stock_code=data.target_stock_code,
        records=data.records,
        sector=data.sector,
        base_date=data.base_date,
    )
    base_result = _result_from_comparison(comparison)
    # 주의: "mock"/"fallback"/"데모용" 문자열은 guardrail.mock_data_audit가 mock으로 오판하므로
    # 실데이터인 MCP 결과의 warning에는 사용하지 않는다(DB 미연결 사유만 중립 표현으로 기록).
    base_result = base_result.model_copy(
        update={
            "warnings": list(base_result.warnings) + [f"db_unavailable_reason: {reason}"],
        }
    )
    narrative = _generate_narrative(comparison)
    return _apply_narrative(base_result, narrative)


def _mock_fallback_result(reason: str) -> CompetitorResult:
    return CompetitorResult(
        score=60,
        peer_summary=(
            "DB 연결 실패로 실제 peer 비교를 완료하지 못해 Phase 1 데모용 mock 경쟁사 비교를 사용했습니다. "
            "실제 투자 판단 전에는 최신 재무/가격 데이터로 다시 확인해야 합니다."
        ),
        peers=[
            {
                "stock_code": "005930",
                "corp_code": "00126380",
                "corp_name": "삼성전자",
                "sector": "반도체",
                "market_cap": None,
                "close_price": None,
                "per": 18.4,
                "pbr": 1.35,
                "roe": 0.078,
                "revenue_growth": None,
                "operating_margin": None,
                "debt_ratio": None,
                "data_quality_score": 0,
            },
            {
                "stock_code": "000660",
                "corp_code": "00164779",
                "corp_name": "SK하이닉스",
                "sector": "반도체",
                "market_cap": None,
                "close_price": None,
                "per": 22.7,
                "pbr": 1.92,
                "roe": 0.085,
                "revenue_growth": None,
                "operating_margin": None,
                "debt_ratio": None,
                "data_quality_score": 0,
            },
            {
                "stock_code": "000990",
                "corp_code": "00126447",
                "corp_name": "DB하이텍",
                "sector": "반도체",
                "market_cap": None,
                "close_price": None,
                "per": 11.8,
                "pbr": 0.88,
                "roe": 0.064,
                "revenue_growth": None,
                "operating_margin": None,
                "debt_ratio": None,
                "data_quality_score": 0,
            },
        ],
        evidence=[
            "mock_data_fallback: DB 연결 실패로 실제 peer_tool 결과 대신 데모용 비교 데이터를 사용했습니다.",
            "mock 데이터는 PER, PBR, ROE 예시값만 포함하며 최신 시장 데이터가 아닙니다.",
            f"fallback 사유: {reason}",
        ],
        peer_selection_summary=(
            "fallback: DB 연결 실패로 같은 섹터 후보를 조회하지 못해 Phase 1 데모용 mock peer 3개를 사용했습니다."
        ),
        metric_definitions={
            "fallback": "DB 연결 실패 시 Phase 1 데모가 중단되지 않도록 제공되는 mock 비교 결과입니다.",
            "per": "mock 예시 PER입니다. 실제 DB 기반 값이 아닙니다.",
            "pbr": "mock 예시 PBR입니다. 실제 DB 기반 값이 아닙니다.",
            "roe": "mock 예시 ROE입니다. 실제 DB 기반 값이 아닙니다.",
            "score": "fallback 상황에서 데모 흐름 유지를 위해 부여한 보수적 점수입니다.",
        },
        relative_position={
            "fallback": "mock_data_fallback",
            "valuation_percentile": None,
            "roe_percentile": None,
            "growth_percentile": None,
            "operating_margin_percentile": None,
            "balance_sheet_percentile": None,
            "data_quality_score": 0,
        },
        data_quality_flags=[
            "mock_data_fallback",
            "fallback_db_connection_failed",
            "실제 DB 기반 peer 비교가 아니므로 결과 해석에 주의가 필요합니다.",
        ],
        a1_peer_multiple_payload={
            "fallback": "mock_data_fallback",
            "median_per": 18.4,
            "median_pbr": 1.35,
        },
        warnings=[
            "mock_data_fallback: DB 연결 실패로 Phase 1 데모용 mock 데이터를 사용했습니다.",
            f"fallback_reason: {reason}",
        ],
    )


def run_competitor(state: AgentState) -> AgentState:
    if state.curator is None:
        raise ValueError("curator result is required before competitor analysis")

    try:
        with get_connection() as conn:
            comparison = build_peer_comparison(
                conn,
                stock_code=state.curator.stock_code,
                sector=state.curator.sector,
            )
        base_result = _result_from_comparison(comparison)
        narrative = _generate_narrative(comparison)
        state.competitor = _apply_narrative(base_result, narrative)
    except Exception as exc:
        if not should_fallback(exc):
            raise
        reason = f"{exc.__class__.__name__}: {exc}"
        # 폴백 우선순위: ① MCP 실시간 시세(실데이터) → ② 하드코딩 mock(최후 보루)
        state.competitor = _mcp_fallback_result(state, reason) or _mock_fallback_result(reason)

    return state
