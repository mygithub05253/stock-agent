"""Guardrail 게이팅·관측 회귀 테스트."""

from __future__ import annotations

import pytest

from stock_agent.agents.guardrail import run_guardrail
from stock_agent.schemas.analysis import (
    AgentState,
    CompetitorResult,
    Portfolio,
    QualResult,
    StrategistResult,
    UserProfile,
)


def _base_state(strategist: StrategistResult) -> AgentState:
    return AgentState(
        user_query="삼성전자 봐줘",
        user_profile=UserProfile(),
        portfolio=Portfolio(),
        strategist=strategist,
    )


def _healthy_strategist() -> StrategistResult:
    return StrategistResult(
        signal="HOLD",
        confidence=62,
        suitability=60,
        headline="보유 유지 검토가 우세합니다.",
        key_reasons=["정량 근거 A", "정성 근거 B", "Peer 비교 C"],
        risks=["리스크 1"],
        next_actions=["분할 매수 기준 설정"],
    )


def test_guardrail_passes_healthy_result() -> None:
    state = run_guardrail(_base_state(_healthy_strategist()))

    assert state.guardrail is not None
    assert state.guardrail.passed is True
    assert state.guardrail.needs_revision is False
    assert state.guardrail.risk_level == "low"
    assert state.guardrail.trace_id  # 관측 trace_id가 부여됨
    assert {c["name"] for c in state.guardrail.checks} == {
        "banned_phrase",
        "evidence_sufficiency",
        "signal_confidence_coherence",
        "mock_data_audit",
    }


def test_guardrail_blocks_and_requests_revision_on_thin_evidence() -> None:
    thin = _healthy_strategist().model_copy(update={"key_reasons": ["단일 근거"]})

    state = run_guardrail(_base_state(thin))

    assert state.guardrail is not None
    assert state.guardrail.passed is False  # 근거 부족 → 출력 차단
    assert state.guardrail.needs_revision is True  # Strategist 재합성 요청
    assert state.guardrail.risk_level == "high"


def test_guardrail_softens_banned_phrase() -> None:
    pushy = _healthy_strategist().model_copy(
        update={"headline": "이 종목은 무조건 매수 해야 하며 수익 보장 수준입니다."}
    )

    state = run_guardrail(_base_state(pushy))

    assert state.guardrail is not None
    assert "무조건 매수" not in state.guardrail.revised_headline
    assert "수익 보장" not in state.guardrail.revised_headline
    assert any("완화" in w for w in state.guardrail.warnings)


def test_guardrail_flags_signal_confidence_contradiction() -> None:
    contradictory = _healthy_strategist().model_copy(
        update={"signal": "BUY", "confidence": 30}
    )

    state = run_guardrail(_base_state(contradictory))

    assert state.guardrail is not None
    assert state.guardrail.passed is True  # 차단은 아니지만
    assert state.guardrail.needs_revision is True  # 재합성 대상
    assert state.guardrail.risk_level == "medium"


def test_guardrail_audits_mock_data_dependency() -> None:
    state = _base_state(_healthy_strategist())
    state.competitor = CompetitorResult(
        score=60,
        peer_summary="mock 비교",
        peers=[],
        evidence=[],
        data_quality_flags=["mock_data_fallback"],
    )
    state.qual = QualResult(
        score=50,
        sentiment="neutral",
        event_types=[],
        evidence=["근거"],
        risks=["mock 뉴스 데이터"],
    )

    result = run_guardrail(state)

    assert result.guardrail is not None
    assert result.guardrail.passed is True
    assert result.guardrail.risk_level == "medium"
    assert any("mock/fallback" in w for w in result.guardrail.warnings)
    audit = next(c for c in result.guardrail.checks if c["name"] == "mock_data_audit")
    assert audit["passed"] is False


def test_guardrail_requires_strategist() -> None:
    state = AgentState(
        user_query="x",
        user_profile=UserProfile(),
        portfolio=Portfolio(),
    )
    with pytest.raises(ValueError):
        run_guardrail(state)
