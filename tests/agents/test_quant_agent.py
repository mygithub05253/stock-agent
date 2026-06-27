from unittest.mock import MagicMock

import pytest

from stock_agent.agents import quant as quant_module
from stock_agent.schemas.analysis import AgentState, CuratorResult, Portfolio, UserProfile


def _make_state() -> AgentState:
    return AgentState(
        user_query="삼성전자 퀀트 테스트",
        user_profile=UserProfile(),
        portfolio=Portfolio(),
        curator=CuratorResult(
            intent="stock_analysis",
            corp_name="삼성전자",
            stock_code="005930",
            corp_code="00126380",
            sector="semiconductor",
        ),
        as_of_date="2026-05-26",
    )


def test_run_quant_returns_db_metrics_when_tools_succeed(monkeypatch):
    conn = MagicMock()
    conn.close = MagicMock()

    monkeypatch.setattr(quant_module, "_connect_with_retry", lambda: (conn, []))
    monkeypatch.setattr(
        quant_module,
        "get_price_metrics",
        lambda _conn, stock_code, as_of_date: {
            "per": 10.0,
            "pbr": 1.1,
            "close_price": 65000,
        },
    )
    monkeypatch.setattr(
        quant_module,
        "get_financial_metrics",
        lambda _conn, corp_code, as_of_date: {
            "roe": 12.0,
            "revenue_growth_yoy": 6.0,
            "operating_margin": 15.0,
            "debt_ratio": 80.0,
        },
    )

    state = _make_state()
    result = quant_module.run_quant(state)

    assert result is state
    assert result.quant is not None
    assert result.quant.score == 80
    assert result.quant.valuation_signal == "BUY"
    assert result.quant.metrics["per"] == 10.0
    assert result.quant.metrics["pbr"] == 1.1
    assert result.quant.metrics["close_price"] == 65000
    assert any("DB에서 조회했습니다" in reason for reason in result.quant.reasons)
    assert not any("fallback" in reason.lower() for reason in result.quant.reasons + result.quant.risks)


def test_run_quant_partial_price_tool_failure_uses_fallback(monkeypatch):
    conn = MagicMock()
    conn.close = MagicMock()

    monkeypatch.setattr(quant_module, "_connect_with_retry", lambda: (conn, []))
    monkeypatch.setattr(
        quant_module,
        "get_price_metrics",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("no price data")),
    )
    monkeypatch.setattr(
        quant_module,
        "get_financial_metrics",
        lambda _conn, corp_code, as_of_date: {
            "roe": 12.0,
            "revenue_growth_yoy": 6.0,
            "operating_margin": 15.0,
            "debt_ratio": 80.0,
        },
    )

    state = _make_state()
    result = quant_module.run_quant(state)

    assert result.quant is not None
    assert result.quant.metrics["per"] == 18.0
    assert result.quant.metrics["pbr"] == 1.3
    assert result.quant.metrics["roe"] == 12.0
    assert any("시세 도구 오류" in reason for reason in result.quant.reasons)
    assert any("임시 기준값" in reason for reason in result.quant.reasons)
    assert any("보수적으로 해석" in risk for risk in result.quant.risks)
    assert result.quant.valuation_signal == "BUY"


def test_run_quant_partial_fin_tool_failure_uses_fallback(monkeypatch):
    conn = MagicMock()
    conn.close = MagicMock()

    monkeypatch.setattr(quant_module, "_connect_with_retry", lambda: (conn, []))
    monkeypatch.setattr(
        quant_module,
        "get_price_metrics",
        lambda _conn, stock_code, as_of_date: {
            "per": 10.0,
            "pbr": 1.1,
            "close_price": 65000,
        },
    )
    monkeypatch.setattr(
        quant_module,
        "get_financial_metrics",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("DART data missing")),
    )

    state = _make_state()
    result = quant_module.run_quant(state)

    assert result.quant is not None
    assert result.quant.metrics["per"] == 10.0
    assert result.quant.metrics["roe"] == 8.0
    assert any("DART 재무 도구 오류" in reason for reason in result.quant.reasons)
    assert any("임시 기준값" in reason for reason in result.quant.reasons)
    assert any("보수적으로 해석" in risk for risk in result.quant.risks)
    assert result.quant.valuation_signal == "HOLD"


def test_run_quant_db_connection_failure_uses_fallback_reasons(monkeypatch):
    monkeypatch.setattr(
        quant_module,
        "_connect_with_retry",
        lambda: (None, ["DB 연결 시도 1 실패: OperationalError: connection refused"]),
    )

    state = _make_state()
    result = quant_module.run_quant(state)

    assert result.quant is not None
    assert result.quant.metrics["per"] == 18.0
    assert result.quant.metrics["roe"] == 8.0
    assert any("DB 연결 시도 1 실패" in reason for reason in result.quant.reasons)
    assert any("임시 기준값" in reason for reason in result.quant.reasons)
    assert any("보수적으로 해석" in risk for risk in result.quant.risks)


def test_run_quant_raises_without_curator():
    state = AgentState(user_query="테스트", user_profile=UserProfile(), portfolio=Portfolio())

    with pytest.raises(ValueError, match="Curator result is required"):
        quant_module.run_quant(state)



print("test end")
