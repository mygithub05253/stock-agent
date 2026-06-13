"""Guardrail 에이전트 — 출력 게이팅 + 관측.

기존 구현은 `passed=True` 고정으로 사실상 게이트가 없었다. 이 버전은 4개 검증을 수행하고
결함 유형에 따라 ① 출력 차단(passed=False) ② Strategist 재합성 요청(needs_revision) ③ 리스크
경고를 구분한다. 모든 검증 과정은 `Trace` span으로 관측되며 결과는 `checks`에 보존된다.

PR #52(공유 fallback 헬퍼) 통합: mock_data_audit가 qual.evidence/risks와 competitor의
data_quality_flags/warnings를 함께 검사해 fallback 근거를 일관되게 경고한다.
"""

from __future__ import annotations

from stock_agent.observability import Trace, flush
from stock_agent.schemas.analysis import AgentState, GuardrailResult

_BANNED_PHRASES = {
    "무조건 매수": "매수 우위의 분석 신호",
    "무조건 매도": "매도 우위의 분석 신호",
    "수익 보장": "수익 가능성",
    "확실한 수익": "기대 수익",
}

_DISCLAIMER = (
    "본 결과는 투자 권유가 아니라 데이터 기반 분석 신호입니다. "
    "최종 투자 판단과 책임은 사용자에게 있습니다."
)

# mock/fallback 데이터를 식별하는 마커. 실데이터 연결 전까지 신뢰도를 보수적으로 표기하기 위함.
_MOCK_MARKERS = ("mock", "fallback", "데모용")


def _looks_like_mock(values: list[str]) -> bool:
    return any(any(marker in value.lower() for marker in _MOCK_MARKERS) for value in values)


def run_guardrail(state: AgentState) -> AgentState:
    if state.strategist is None:
        raise ValueError("strategist result is required before guardrail")

    trace = Trace(name="guardrail")
    strategist = state.strategist
    headline = strategist.headline
    warnings: list[str] = []
    checks: list[dict[str, str | bool]] = []

    # 1) 표현 게이트 — 투자 권유성 금지 표현 완화 (항상 통과, 정보성)
    with trace.span("banned_phrase_filter") as span:
        replaced: list[str] = []
        for banned, replacement in _BANNED_PHRASES.items():
            if banned in headline:
                headline = headline.replace(banned, replacement)
                replaced.append(banned)
                warnings.append(f"투자 권유성 표현을 완화했습니다: {banned}")
        span.attributes["replaced"] = replaced
        checks.append(
            {
                "name": "banned_phrase",
                "passed": True,
                "severity": "info",
                "detail": f"{len(replaced)}건 완화" if replaced else "위반 없음",
            }
        )

    # 2) 차단 게이트 — 근거 충분성. key_reasons가 2건 미만이면 출력 차단 + 재합성 요청.
    with trace.span("evidence_sufficiency") as span:
        reasons = [reason for reason in strategist.key_reasons if reason and reason.strip()]
        evidence_ok = len(reasons) >= 2
        span.attributes["reason_count"] = len(reasons)
        checks.append(
            {
                "name": "evidence_sufficiency",
                "passed": evidence_ok,
                "severity": "block",
                "revisable": True,
                "detail": f"key_reasons {len(reasons)}건",
            }
        )
        if not evidence_ok:
            warnings.append("핵심 근거가 부족해 최종 출력을 보류하고 재합성이 필요합니다.")

    # 3) 정합성 게이트 — 신호와 신뢰도가 상충하면 경고 + 재합성 요청 (차단까지는 아님).
    with trace.span("signal_confidence_coherence") as span:
        coherent = not (
            (strategist.signal == "BUY" and strategist.confidence < 50)
            or (strategist.signal == "SELL" and strategist.confidence > 60)
        )
        span.attributes.update(signal=strategist.signal, confidence=strategist.confidence)
        checks.append(
            {
                "name": "signal_confidence_coherence",
                "passed": coherent,
                "severity": "warn",
                "revisable": True,
                "detail": f"{strategist.signal}@{strategist.confidence}",
            }
        )
        if not coherent:
            warnings.append(
                f"신호({strategist.signal})와 신뢰도({strategist.confidence})가 상충해 재검토가 필요합니다."
            )

    # 4) 리스크 게이트 — mock/fallback 데이터 의존도 감사 (재합성으로 못 고침, 신뢰도 경고만).
    #    PR #52 통합: qual.evidence와 competitor.warnings의 fallback 근거까지 함께 검사한다.
    with trace.span("mock_data_audit") as span:
        mock_sources: list[str] = []
        if state.competitor is not None and _looks_like_mock(
            list(state.competitor.data_quality_flags) + list(state.competitor.warnings)
        ):
            mock_sources.append("competitor")
        if state.qual is not None and _looks_like_mock(
            list(state.qual.risks) + list(state.qual.evidence)
        ):
            mock_sources.append("qual")
        if state.quant is not None and _looks_like_mock([str(v) for v in state.quant.metrics.values()]):
            mock_sources.append("quant")
        span.attributes["mock_sources"] = mock_sources
        if mock_sources:
            warnings.append(
                "다음 근거가 mock/fallback 데이터입니다: "
                + ", ".join(mock_sources)
                + ". 실데이터 연결 전까지 신뢰도를 보수적으로 해석하세요."
            )
        checks.append(
            {
                "name": "mock_data_audit",
                "passed": len(mock_sources) == 0,
                "severity": "warn",
                "revisable": False,
                "detail": ", ".join(mock_sources) if mock_sources else "실데이터",
            }
        )

    # 종합 판정
    blocked = any(not c["passed"] and c.get("severity") == "block" for c in checks)
    revisable_fail = any(not c["passed"] and c.get("revisable") for c in checks)
    warn_fail = any(not c["passed"] and c.get("severity") == "warn" for c in checks)

    passed = not blocked
    needs_revision = revisable_fail
    risk_level = "high" if blocked else "medium" if warn_fail else "low"

    state.guardrail = GuardrailResult(
        passed=passed,
        needs_revision=needs_revision,
        risk_level=risk_level,
        checks=[{k: v for k, v in c.items() if k != "revisable"} for c in checks],
        trace_id=trace.trace_id,
        warnings=warnings,
        revised_headline=headline,
        disclaimer=_DISCLAIMER,
    )
    flush(trace)
    return state
