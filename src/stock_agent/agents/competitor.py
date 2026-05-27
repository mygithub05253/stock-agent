from stock_agent.schemas.analysis import AgentState, CompetitorResult
from stock_agent.tools.peer_tool import PeerComparison, build_peer_comparison

try:
    from stock_agent.db import get_connection
except ModuleNotFoundError as exc:
    if exc.name != "psycopg":
        raise

    def get_connection():
        raise RuntimeError("psycopg is required to connect to the DB.")


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
        state.competitor = _result_from_comparison(comparison)
    except Exception as exc:
        state.competitor = _mock_fallback_result(f"{exc.__class__.__name__}: {exc}")

    return state
