import re
from typing import Optional

from stock_agent.schemas.analysis import AgentState, GuardrailResult, StrategistResult
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


_PII_EMAIL_RE = re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_PII_PHONE_RE = re.compile(r"\b\d{2,3}[-\s]?\d{3,4}[-\s]?\d{4}\b")
_PROFANITY = {"fuck", "shit", "damn", "씨발", "좆"}
_GUARANTEE_RE = re.compile(r"\b(guarantee|guaranteed|risk[- ]?free|will\s+be|will\s+make|ensure|assure|보장|무위험|확실히|반드시|100%)\b", re.I)
_PERCENT_RETURN_RE = re.compile(r"\b\d{1,3}%\s*(return|수익|수익률)\b", re.I)

# Additional banned phrases and language-specific risky phrases
_BANNED_PHRASES = {
    "한국": ["무조건", "확실한 수익", "절대 손실 없음", "100% 수익"],
}

_DISCLAIMER = (
    "본 결과는 투자 권유가 아니라 데이터 기반 분석 신호입니다. "
    "최종 투자 판단과 책임은 사용자에게 있습니다."
)

# mock/fallback 데이터를 식별하는 마커. 실데이터 연결 전까지 신뢰도를 보수적으로 표기하기 위함.
_MOCK_MARKERS = ("mock", "fallback", "데모용")


def _looks_like_mock(values: list[str]) -> bool:
    return any(any(marker in value.lower() for marker in _MOCK_MARKERS) for value in values)


def _contains_pii(text: Optional[str]) -> bool:
    if not text:
        return False
    if _PII_EMAIL_RE.search(text):
        return True
    if _PII_PHONE_RE.search(text):
        return True
    return False


def _contains_profanity(text: Optional[str]) -> bool:
    if not text:
        return False
    low = text.lower()
    return any(word in low for word in _PROFANITY)


def _contains_guarantee(text: Optional[str]) -> bool:
    if not text:
        return False
    if _GUARANTEE_RE.search(text):
        return True
    if _PERCENT_RETURN_RE.search(text):
        return True
    return False


def _soften_headline(headline: str) -> str:
    # basic, conservative rewrites to avoid strong guarantees
    h = headline
    h = re.sub(r"\bwill\b", "may", h, flags=re.I)
    # remove explicit guarantee/assurance words rather than reintroducing them
    h = re.sub(r"\bguarantee(s?|d)?\b", "", h, flags=re.I)
    h = re.sub(r"\bensure(s?|d)?\b", "", h, flags=re.I)
    h = re.sub(r"\bassure(s?|d)?\b", "", h, flags=re.I)
    h = re.sub(r"\bno\s*risk\b", "reduced visibility on risk", h, flags=re.I)
    # replace explicit percent-return statements with non-numeric phrasing
    h = _PERCENT_RETURN_RE.sub("significant return", h)

    # strip multiple spaces introduced by removals
    h = re.sub(r"\s{2,}", " ", h).strip()
    if not h.endswith(" [수정됨]"):
        h = h + " [수정됨]"
    return h


def run_guardrail(state: AgentState, evidence_bundle: Optional[dict] = None, policy: Optional[dict] = None) -> AgentState:
    """Run guardrail checks on the strategist output and attach GuardrailResult to state.

    This performs lightweight, deterministic checks:
    - PII detection (emails/phones)
    - Profanity detection
    - Investment-guarantee / absolute claim detection
    - Evidence sufficiency (basic)

    The function does not call external services and is safe to run synchronously.
    """
    if state.strategist is None:
        raise ValueError("Strategist result required for guardrail evaluation")

    strat: StrategistResult = state.strategist
    passed = True
    warnings: list[str] = []
    revised_headline = strat.headline or ""

    # PII checks
    if _contains_pii(str(state.user_query)):
        passed = False
        warnings.append("PII detected in user query — input rejected or redacted")

    if _contains_pii(revised_headline) or any(_contains_pii(r) for r in strat.key_reasons):
        passed = False
        warnings.append("PII detected in strategist output — redaction required")

    # Profanity checks
    if _contains_profanity(str(state.user_query)) or _contains_profanity(revised_headline) or any(_contains_profanity(r) for r in strat.key_reasons):
        passed = False
        warnings.append("Inappropriate language detected in inputs/outputs")

    # Guarantee / absolute claim detection
    guarantee_found = _contains_guarantee(revised_headline) or any(_contains_guarantee(r) for r in strat.key_reasons)
    if guarantee_found:
        passed = False
        warnings.append("Potential investment-guarantee or absolute claim detected and softened")
        revised_headline = _soften_headline(revised_headline or strat.headline)

    # Evidence sufficiency: require at least one key reason and non-empty next_actions
    if not strat.key_reasons or len(strat.key_reasons) < 1:
        warnings.append("Insufficient explicit supporting reasons provided by strategist")

    # Build disclaimer
    disclaimer_lines = []
    disclaimer_lines.append("본 분석은 교육 및 정보 제공 목적이며 투자 권유가 아닙니다.")
    disclaimer_lines.append("투자 결정은 본인의 판단과 책임으로 진행하시기 바랍니다.")
    if not passed:
        disclaimer_lines.append("일부 문구가 위험 검출로 인해 완화되었거나 출력이 제한되었습니다.")

    disclaimer = " ".join(disclaimer_lines)

    guardrail_result = GuardrailResult(
        passed=passed,
        warnings=warnings,
        revised_headline=revised_headline,
        disclaimer=disclaimer,
    )

    state.guardrail = guardrail_result
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

