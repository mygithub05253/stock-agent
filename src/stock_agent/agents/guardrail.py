from __future__ import annotations

import re
from typing import Optional

from stock_agent.observability import Trace, flush
from stock_agent.schemas.analysis import AgentState, GuardrailResult, StrategistResult

"""Guardrail 에이전트 — 출력 게이팅 + 안전성 검출 + 관측.

7개 게이트를 수행하고 결함 유형에 따라 ① 출력 차단(passed=False) ② Strategist 재합성 요청
(needs_revision) ③ 리스크 경고를 구분한다. 모든 검증 과정은 `Trace` span으로 관측되며
결과는 `checks`에 보존된다.

통합 이력:
- PR #50(이동원): 게이팅 구조 + 관측(observability) + mock 감사
- PR #52(doyekeem): 공유 fallback 헬퍼 → mock_data_audit가 fallback 근거까지 검사
- PR #54(팀원): PII·욕설·투자보장 표현 검출 + 헤드라인 완화(_soften_headline)

`graph/pipeline.py`의 재작성 루프가 경고 문구("PII", "Inappropriate language",
"guarantee")와 `_soften_headline`을 키로 사용하므로 해당 계약을 유지한다.
"""

# 한국어 투자 권유성 표현 완화 매핑(정보성 게이트). 명시적 치환으로 자연스러운 문구를 유지한다.
_BANNED_PHRASES = {
    "무조건 매수": "매수 우위의 분석 신호",
    "무조건 매도": "매도 우위의 분석 신호",
    "수익 보장": "수익 가능성",
    "확실한 수익": "기대 수익",
}

# 안전성 검출 패턴(PR #54 통합)
_PII_EMAIL_RE = re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_PII_PHONE_RE = re.compile(r"\b\d{2,3}[-\s]?\d{3,4}[-\s]?\d{4}\b")
_PROFANITY = {"fuck", "shit", "damn", "씨발", "좆"}
_GUARANTEE_RE = re.compile(
    r"\b(guarantee|guaranteed|risk[- ]?free|will\s+be|will\s+make|ensure|assure)\b|"
    r"(보장|무위험|확실히|반드시|100%)",
    re.I,
)
_PERCENT_RETURN_RE = re.compile(r"\b\d{1,3}%\s*(return|수익|수익률)\b", re.I)

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
    return bool(_PII_EMAIL_RE.search(text) or _PII_PHONE_RE.search(text))


def _contains_profanity(text: Optional[str]) -> bool:
    if not text:
        return False
    low = text.lower()
    return any(word in low for word in _PROFANITY)


def _contains_guarantee(text: Optional[str]) -> bool:
    if not text:
        return False
    return bool(_GUARANTEE_RE.search(text) or _PERCENT_RETURN_RE.search(text))


def _soften_headline(headline: str) -> str:
    """보장성·단정 표현을 보수적으로 완화한다(pipeline 재작성 루프에서도 호출)."""
    h = headline
    h = re.sub(r"\bwill\b", "may", h, flags=re.I)
    h = re.sub(r"\bguarantee(s?|d)?\b", "", h, flags=re.I)
    h = re.sub(r"\bensure(s?|d)?\b", "", h, flags=re.I)
    h = re.sub(r"\bassure(s?|d)?\b", "", h, flags=re.I)
    h = re.sub(r"\bno\s*risk\b", "reduced visibility on risk", h, flags=re.I)
    h = _PERCENT_RETURN_RE.sub("significant return", h)
    h = re.sub(r"\s{2,}", " ", h).strip()
    if not h.endswith(" [수정됨]"):
        h = h + " [수정됨]"
    return h


def run_guardrail(
    state: AgentState,
    evidence_bundle: Optional[dict] = None,
    policy: Optional[dict] = None,
) -> AgentState:
    """Strategist 출력에 7개 게이트를 적용해 GuardrailResult를 부착한다.

    외부 서비스를 호출하지 않는 결정론적 검증이라 동기 실행에 안전하다.
    `evidence_bundle`/`policy`는 향후 정책 주입용 확장 슬롯(현재 미사용).
    """
    if state.strategist is None:
        raise ValueError("strategist result is required before guardrail")

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

    trace = Trace(name="guardrail")
    strategist = state.strategist
    headline = strategist.headline or ""
    reason_texts = [r for r in strategist.key_reasons if r]
    warnings: list[str] = []
    checks: list[dict[str, str | bool]] = []

    # 1) 표현 게이트 — 한국어 권유성 표현 완화 (정보성, 항상 통과)
    with trace.span("banned_phrase_filter") as span:
        replaced: list[str] = []
        for banned, replacement in _BANNED_PHRASES.items():
            if banned in headline:
                headline = headline.replace(banned, replacement)
                replaced.append(banned)
                warnings.append(f"투자 권유성 표현을 완화했습니다: {banned}")
        span.attributes["replaced"] = replaced
        checks.append(
            {"name": "banned_phrase", "passed": True, "severity": "info",
             "detail": f"{len(replaced)}건 완화" if replaced else "위반 없음"}
        )

    # 2) PII 게이트 (차단) — 이메일/전화번호
    with trace.span("pii") as span:
        pii_found = (
            _contains_pii(str(state.user_query))
            or _contains_pii(headline)
            or any(_contains_pii(r) for r in reason_texts)
        )
        span.attributes["found"] = pii_found
        if pii_found:
            warnings.append("PII detected in inputs/outputs — redaction required")
        checks.append(
            {"name": "pii", "passed": not pii_found, "severity": "block",
             "detail": "PII 검출" if pii_found else "없음"}
        )

    # 3) 욕설 게이트 (차단)
    with trace.span("profanity") as span:
        profanity_found = (
            _contains_profanity(str(state.user_query))
            or _contains_profanity(headline)
            or any(_contains_profanity(r) for r in reason_texts)
        )
        span.attributes["found"] = profanity_found
        if profanity_found:
            warnings.append("Inappropriate language detected in inputs/outputs")
        checks.append(
            {"name": "profanity", "passed": not profanity_found, "severity": "block",
             "detail": "부적절 표현 검출" if profanity_found else "없음"}
        )

    # 4) 투자보장 게이트 (차단 + 헤드라인 완화)
    with trace.span("guarantee") as span:
        guarantee_found = _contains_guarantee(headline) or any(
            _contains_guarantee(r) for r in reason_texts
        )
        span.attributes["found"] = guarantee_found
        if guarantee_found:
            warnings.append(
                "Potential investment-guarantee or absolute claim detected and softened"
            )
            headline = _soften_headline(headline)
        checks.append(
            {"name": "guarantee", "passed": not guarantee_found, "severity": "block",
             "detail": "보장성 표현 완화" if guarantee_found else "없음"}
        )

    # 5) 차단 게이트 — 근거 충분성. key_reasons 2건 미만이면 출력 차단 + 재합성 요청.
    with trace.span("evidence_sufficiency") as span:
        reasons = [r for r in strategist.key_reasons if r and r.strip()]
        evidence_ok = len(reasons) >= 2
        span.attributes["reason_count"] = len(reasons)
        checks.append(
            {"name": "evidence_sufficiency", "passed": evidence_ok, "severity": "block",
             "revisable": True, "detail": f"key_reasons {len(reasons)}건"}
        )
        if not evidence_ok:
            warnings.append("Insufficient evidence — 핵심 근거가 부족해 재합성이 필요합니다.")

    # 6) 정합성 게이트 — 신호와 신뢰도가 상충하면 경고 + 재합성 요청 (차단 아님).
    with trace.span("signal_confidence_coherence") as span:
        coherent = not (
            (strategist.signal == "BUY" and strategist.confidence < 50)
            or (strategist.signal == "SELL" and strategist.confidence > 60)
        )
        span.attributes.update(signal=strategist.signal, confidence=strategist.confidence)
        checks.append(
            {"name": "signal_confidence_coherence", "passed": coherent, "severity": "warn",
             "revisable": True, "detail": f"{strategist.signal}@{strategist.confidence}"}
        )
        if not coherent:
            warnings.append(
                f"신호({strategist.signal})와 신뢰도({strategist.confidence})가 상충해 재검토가 필요합니다."
            )

    # 7) 리스크 게이트 — mock/fallback 데이터 의존도 감사 (재합성으로 못 고침, 신뢰도 경고만).
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
            {"name": "mock_data_audit", "passed": len(mock_sources) == 0, "severity": "warn",
             "revisable": False, "detail": ", ".join(mock_sources) if mock_sources else "실데이터"}
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
