from datetime import date
from unittest.mock import MagicMock

import pytest

from stock_agent.agents import competitor as competitor_module
from stock_agent.schemas.analysis import AgentState, CompetitorResult, CuratorResult, Portfolio, UserProfile
from stock_agent.tools.peer_tool import PeerComparison, PeerMetricRow


def _make_comparison() -> PeerComparison:
    target = PeerMetricRow(
        corp_code="00126380", stock_code="005930", corp_name="삼성전자",
        sector="반도체", market_cap=420_000_000_000_000, data_quality_score=80,
        per=18.4, pbr=1.35, roe=0.078,
    )
    peer = PeerMetricRow(
        corp_code="00164779", stock_code="000660", corp_name="SK하이닉스",
        sector="반도체", market_cap=150_000_000_000_000, data_quality_score=80,
        per=22.0, pbr=1.8, roe=0.085,
    )
    return PeerComparison(
        target=target,
        peers=[peer],
        score=65,
        peer_selection_summary="반도체 섹터 1개 peer",
        peer_summary="기본 룰 기반 요약",
        metric_definitions={"per": "market_cap/net_income"},
        relative_position={"roe_percentile": 0.5},
        evidence=["ROE 50분위"],
        data_quality_flags=[],
        warnings=[],
    )


def _state() -> AgentState:
    return AgentState(
        user_query="삼성전자 peer 비교",
        user_profile=UserProfile(),
        portfolio=Portfolio(),
        curator=CuratorResult(
            intent="peer_compare", corp_name="삼성전자",
            stock_code="005930", corp_code="00126380", sector="반도체",
        ),
    )


def test_cache_key_contains_stock_code_and_date():
    from stock_agent.agents.competitor import _cache_key
    key = _cache_key("005930")
    assert "005930" in key
    assert date.today().isoformat() in key


def test_apply_narrative_updates_peer_summary():
    from stock_agent.agents.competitor import _apply_narrative
    base = CompetitorResult(score=65, peer_summary="기본 요약", peers=[], evidence=[], warnings=[])
    narrative = {
        "peer_summary": "LLM 향상된 요약",
        "evidence_cards": [
            {"finding": "PER 저평가", "metric_basis": "PER 18x vs 22x", "confidence": "high", "flag": "strength"}
        ],
        "bear_case": "ROE 개선 전제 필요",
        "data_gaps": [],
    }
    result = _apply_narrative(base, narrative)
    assert result.peer_summary == "LLM 향상된 요약"
    assert len(result.evidence_cards) == 1
    assert result.evidence_cards[0]["confidence"] == "high"
    assert result.bear_case == "ROE 개선 전제 필요"


def test_apply_narrative_ignores_empty_peer_summary():
    from stock_agent.agents.competitor import _apply_narrative
    base = CompetitorResult(score=65, peer_summary="기본 요약", peers=[], evidence=[], warnings=[])
    result = _apply_narrative(base, {"peer_summary": "  ", "evidence_cards": [], "bear_case": "", "data_gaps": []})
    assert result.peer_summary == "기본 요약"


def test_apply_narrative_returns_base_on_none():
    from stock_agent.agents.competitor import _apply_narrative
    base = CompetitorResult(score=65, peer_summary="요약", peers=[], evidence=[], warnings=[])
    assert _apply_narrative(base, None) is base


def test_generate_narrative_returns_none_when_no_api_key(monkeypatch):
    from stock_agent.agents.competitor import _generate_narrative
    settings_mock = MagicMock()
    settings_mock.openrouter_api_key = None
    monkeypatch.setattr(competitor_module, "get_settings", lambda: settings_mock)
    assert _generate_narrative(_make_comparison()) is None


def test_generate_narrative_uses_cached_value(monkeypatch):
    from stock_agent.agents.competitor import _cache_key, _generate_narrative
    comparison = _make_comparison()
    key = _cache_key(comparison.target.stock_code)
    cached = {"peer_summary": "캐시된 요약", "evidence_cards": [], "bear_case": "", "data_gaps": []}
    competitor_module._narrative_cache[key] = cached

    settings_mock = MagicMock()
    settings_mock.openrouter_api_key = "test-key"
    monkeypatch.setattr(competitor_module, "get_settings", lambda: settings_mock)

    call_count = {"n": 0}

    def fake_chat(*args, **kwargs):
        call_count["n"] += 1
        return {}

    monkeypatch.setattr(competitor_module, "openrouter_chat_json", fake_chat)

    result = _generate_narrative(comparison)
    assert result == cached
    assert call_count["n"] == 0

    del competitor_module._narrative_cache[key]


def test_generate_narrative_returns_none_on_llm_error(monkeypatch):
    from stock_agent.agents.competitor import _cache_key, _generate_narrative
    from stock_agent.llm.openrouter_client import OpenRouterClientError

    comparison = _make_comparison()
    key = _cache_key(comparison.target.stock_code)
    competitor_module._narrative_cache.pop(key, None)

    settings_mock = MagicMock()
    settings_mock.openrouter_api_key = "test-key"
    monkeypatch.setattr(competitor_module, "get_settings", lambda: settings_mock)
    monkeypatch.setattr(competitor_module, "_load_system_prompt", lambda: "prompt")

    def failing_chat(*args, **kwargs):
        raise OpenRouterClientError("rate limited")

    monkeypatch.setattr(competitor_module, "openrouter_chat_json", failing_chat)

    assert _generate_narrative(comparison) is None


def test_run_competitor_applies_narrative_when_llm_succeeds(monkeypatch):
    comparison = _make_comparison()

    class FakeConn:
        def __enter__(self):
            return "conn"

        def __exit__(self, *_):
            pass

    monkeypatch.setattr(competitor_module, "get_connection", FakeConn)
    monkeypatch.setattr(competitor_module, "build_peer_comparison", lambda *a, **kw: comparison)

    llm_result = {
        "peer_summary": "LLM 서술",
        "evidence_cards": [{"finding": "ROE 우위", "metric_basis": "ROE 7.8% vs 8.5%", "confidence": "medium", "flag": "neutral"}],
        "bear_case": "HBM 수요 둔화 시 ROE 악화 가능",
        "data_gaps": [],
    }
    monkeypatch.setattr(competitor_module, "_generate_narrative", lambda _: llm_result)

    result_state = competitor_module.run_competitor(_state())
    assert result_state.competitor is not None
    assert result_state.competitor.peer_summary == "LLM 서술"
    assert result_state.competitor.bear_case == "HBM 수요 둔화 시 ROE 악화 가능"
    assert len(result_state.competitor.evidence_cards) == 1
