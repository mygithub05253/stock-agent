import pytest
from unittest.mock import MagicMock, patch

from stock_agent.schemas.analysis import (
    AgentState, MacroResult,
    UserProfile, Portfolio, CuratorResult,
)


# ── 테스트용 기본 AgentState 생성 헬퍼 ──────────────────────
def _make_state(sector: str = "반도체IT") -> AgentState:
    return AgentState(
        user_query="삼성전자 지금 사도 될까요?",
        user_profile=UserProfile(),
        portfolio=Portfolio(),
        curator=CuratorResult(
            intent="신규 관심 종목 점검",
            corp_name="삼성전자",
            stock_code="005930",
            corp_code="00126380",
            sector=sector,
        ),
    )


# ── 테스트 1: DB 연결 성공 시 정상 동작 ─────────────────────
def test_run_macro_db_success():
    """DB 연결 성공 시 MacroResult가 state.macro에 저장되는지 확인"""
    from stock_agent.agents.macro import run_macro

    mock_context = {
        "indicators": {
            "한국은행 기준금리":          {"value": 3.0},
            "소비자물가지수 (CPI)":       {"value": 1.8},
            "실질 GDP 성장률 (전년동기비)": {"value": 2.5},
            "뉴스심리지수":               {"value": 105.0},
            "원/달러 환율":               {"value": 1380.0},
        }
    }

    with patch("stock_agent.agents.macro.psycopg2.connect") as mock_conn, \
         patch("stock_agent.agents.macro.get_macro_context", return_value=mock_context), \
         patch("stock_agent.agents.macro._fetch_prev_context", return_value=None):
        mock_conn.return_value.__enter__ = MagicMock()
        state = _make_state("반도체IT")
        result = run_macro(state)

    assert result.macro is not None
    assert isinstance(result.macro, MacroResult)
    assert 0 <= result.macro.score <= 100
    assert result.macro.macro_signal in ("BUY", "HOLD", "SELL")
    assert result.macro.sector == "반도체IT"


# ── 테스트 2: DB 연결 실패 시 fallback 동작 ─────────────────
def test_run_macro_db_failure_fallback():
    """DB 연결 실패 시 mock fallback으로 파이프라인이 계속 동작하는지 확인"""
    from stock_agent.agents.macro import run_macro
    import psycopg2

    with patch("stock_agent.agents.macro.psycopg2.connect",
               side_effect=psycopg2.OperationalError("connection refused")):
        state = _make_state("금융")
        result = run_macro(state)

    assert result.macro is not None
    assert result.macro.score >= 0
    # fallback 경고가 risks에 포함되어야 함
    assert any("fallback" in r.lower() or "DB 연결 실패" in r for r in result.macro.risks)


# ── 테스트 3: Curator 없을 때 ValueError ────────────────────
def test_run_macro_no_curator():
    """Curator 결과 없으면 ValueError 발생해야 함"""
    from stock_agent.agents.macro import run_macro

    state = AgentState(
        user_query="삼성전자?",
        user_profile=UserProfile(),
        portfolio=Portfolio(),
    )
    with pytest.raises(ValueError, match="Curator result is required"):
        run_macro(state)


# ── 테스트 4: 섹터별 점수 차이 검증 ─────────────────────────
def test_run_macro_sector_difference():
    """반도체IT vs 건설부동산 — 고금리 환경에서 점수가 달라야 함"""
    from stock_agent.agents.macro import run_macro

    # 고금리(3.8%) mock 데이터
    mock_context = {
        "indicators": {
            "한국은행 기준금리":          {"value": 3.8},
            "소비자물가지수 (CPI)":       {"value": 2.5},
            "실질 GDP 성장률 (전년동기비)": {"value": 1.5},
            "뉴스심리지수":               {"value": 100.0},
            "원/달러 환율":               {"value": 1400.0},
        }
    }

    with patch("stock_agent.agents.macro.psycopg2.connect"), \
         patch("stock_agent.agents.macro.get_macro_context", return_value=mock_context), \
         patch("stock_agent.agents.macro._fetch_prev_context", return_value=None):

        state_semi = _make_state("반도체IT")
        result_semi = run_macro(state_semi)

        state_const = _make_state("건설부동산")
        result_const = run_macro(state_const)

    # 건설부동산은 고금리에서 더 낮은 점수를 받아야 함
    assert result_const.macro.score < result_semi.macro.score, (
        f"건설({result_const.macro.score}) >= 반도체({result_semi.macro.score})"
    )


# ── 테스트 5: RoC 데이터 부족 시 graceful 처리 ──────────────
def test_run_macro_roc_no_data():
    """이전 시점 데이터 없어도 에러 없이 동작해야 함"""
    from stock_agent.agents.macro import run_macro

    mock_context = {
        "indicators": {
            "한국은행 기준금리": {"value": 3.5},
            "소비자물가지수 (CPI)": {"value": 2.0},
            "실질 GDP 성장률 (전년동기비)": {"value": 2.0},
            "뉴스심리지수": {"value": 100.0},
            "원/달러 환율": {"value": 1350.0},
        }
    }

    with patch("stock_agent.agents.macro.psycopg2.connect"), \
         patch("stock_agent.agents.macro.get_macro_context", return_value=mock_context), \
         patch("stock_agent.agents.macro._fetch_prev_context", return_value=None):
        state = _make_state("금융")
        result = run_macro(state)

    # RoC 데이터 없어도 정상 동작
    assert result.macro is not None
    assert result.macro.rate_of_change == {}