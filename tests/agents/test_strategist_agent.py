"""Strategist 부분 실패 허용(graceful degradation) 회귀 테스트."""

from __future__ import annotations

import pytest

from stock_agent.agents.strategist import run_strategist
from stock_agent.schemas.analysis import (
    AgentState,
    CompetitorResult,
    MacroResult,
    Portfolio,
    QualResult,
    QuantResult,
    UserProfile,
)


def _quant(score: int = 60) -> QuantResult:
    return QuantResult(
        score=score,
        valuation_signal="HOLD",
        metrics={"per": 18.0},
        reasons=["정량 근거"],
        risks=["정량 리스크"],
    )


def _qual(score: int = 55) -> QualResult:
    return QualResult(
        score=score,
        sentiment="neutral",
        event_types=["earnings"],
        evidence=["정성 근거"],
        risks=["정성 리스크"],
    )


def _competitor(score: int = 60) -> CompetitorResult:
    return CompetitorResult(score=score, peer_summary="peer 비교", peers=[], evidence=["peer 근거"])


def _macro(score: int = 50) -> MacroResult:
    return MacroResult(
        score=score,
        macro_signal="HOLD",
        indicators={},
        reasons=["거시 근거"],
        risks=["거시 리스크"],
        sector="반도체",
        as_of_date="2026-05-21",
    )


def _state(**workers) -> AgentState:
    state = AgentState(
        user_query="삼성전자 봐줘",
        user_profile=UserProfile(),
        portfolio=Portfolio(),
    )
    for name, value in workers.items():
        setattr(state, name, value)
    return state


def test_strategist_full_inputs_not_degraded() -> None:
    state = run_strategist(_state(quant=_quant(), qual=_qual(), competitor=_competitor(), macro=_macro()))

    assert state.strategist is not None
    assert state.strategist.degraded is False
    assert state.strategist.contributing_agents == ["quant", "qual", "competitor", "macro"]
    # 전 워커가 있으면 신뢰도는 종합 점수와 동일(누락 차감 0).
    expected = round(60 * 0.40 + 55 * 0.25 + 60 * 0.20 + 50 * 0.15)
    assert state.strategist.confidence == expected


def test_strategist_degrades_when_qual_missing() -> None:
    full = run_strategist(_state(quant=_quant(), qual=_qual(), competitor=_competitor()))
    degraded = run_strategist(_state(quant=_quant(), competitor=_competitor()))

    assert degraded.strategist is not None
    assert degraded.strategist.degraded is True
    assert "qual" not in degraded.strategist.contributing_agents
    # 누락 워커 1개당 신뢰도 10점 차감 → 완전 입력 대비 낮아야 한다.
    assert degraded.strategist.confidence < full.strategist.confidence
    # 정성 근거가 빠져도 크래시 없이 종합되어야 한다.
    assert degraded.strategist.key_reasons
    assert any("qual" in risk for risk in degraded.strategist.risks)


def test_strategist_raises_when_all_fundamentals_missing() -> None:
    with pytest.raises(ValueError):
        run_strategist(_state(macro=_macro()))


def test_strategist_macro_absent_keeps_legacy_weights() -> None:
    # Macro가 없을 때 quant=80, qual=60, competitor=40 → 0.45/0.30/0.25 = 58 (HOLD)
    state = run_strategist(_state(quant=_quant(80), qual=_qual(60), competitor=_competitor(40)))

    assert state.strategist is not None
    assert state.strategist.confidence == round(80 * 0.45 + 60 * 0.30 + 40 * 0.25)
    assert state.strategist.degraded is False
