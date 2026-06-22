from __future__ import annotations

import operator
from typing import Annotated, Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from stock_agent.agents import (
    run_competitor,
    run_curator,
    run_guardrail,
    run_investment_analyst,
    run_macro,
    run_qual,
    run_quant,
    run_request_classifier,
    run_strategist,
    run_result_renderer,
)
from stock_agent.schemas.analysis import (
    AgentState,
    AnalysisOutput,
    CompetitorResult,
    CuratorResult,
    GuardrailResult,
    Holding,
    MacroResult,
    Portfolio,
    QualResult,
    QuantResult,
    StrategistResult,
    Tier1Result,
    UserProfile,
    UserRequest,
)


class AnalysisGraphState(TypedDict, total=False):
    user_query: str
    user_request: UserRequest | None
    user_profile: UserProfile
    portfolio: Portfolio
    as_of_date: str | None
    curator: CuratorResult | None
    quant: QuantResult | None
    qual: QualResult | None
    competitor: CompetitorResult | None
    macro: MacroResult | None
    strategist: StrategistResult | None
    guardrail: GuardrailResult | None
    investment_report: dict[str, str] | None
    rendered_report: dict[str, str | int | list[str]] | None
    graph_route: dict[str, Any]
    trace_spans: Annotated[list[str], operator.add]
    worker_errors: Annotated[list[str], operator.add]


_AGENT_FIELDS = set(AgentState.model_fields)
_EVENT_LABELS = {
    "curator": "Curator",
    "classifier": "RequestClassifier",
    "quant": "Quant",
    "qual": "Qual",
    "competitor": "Competitor",
    "macro": "Macro",
    "strategist": "Strategist",
    "investment_analyst": "InvestmentAnalyst",
    "guardrail": "Guardrail",
    "guardrail_apply": "Guardrail Apply",
}

# ==========================================
# worker 이름 → 실행 함수 / 결과 필드 매핑
# Send API fan-out에서 동적으로 참조
# ==========================================
_WORKER_RUNNERS: dict[str, tuple[Callable, str]] = {
    "quant":      (run_quant,       "quant"),
    "qual":       (run_qual,        "qual"),
    "competitor": (run_competitor,  "competitor"),
    "macro":      (run_macro,       "macro"),
}


def build_demo_profile() -> tuple[UserProfile, Portfolio]:
    return (
        UserProfile(
            user_id="demo-park",
            risk_tolerance="medium",
            investment_horizon_months=12,
            cash_source="surplus_cash",
            preferred_sectors=["반도체", "AI 인프라"],
        ),
        Portfolio(
            holdings=[
                Holding(
                    stock_code="005930",
                    corp_name="삼성전자",
                    sector="반도체",
                    weight=0.32,
                    avg_price=72000,
                    qty=10,
                    current_price=78000,
                ),
                Holding(
                    stock_code="000660",
                    corp_name="SK하이닉스",
                    sector="반도체",
                    weight=0.18,
                    avg_price=185000,
                    qty=3,
                    current_price=201000,
                ),
            ],
            cash_weight=0.2,
        ),
    )


def _agent_state(state: AnalysisGraphState) -> AgentState:
    return AgentState(**{key: value for key, value in state.items() if key in _AGENT_FIELDS})


def _patch_from_agent(state: AgentState, *fields: str) -> dict[str, Any]:
    return {field: getattr(state, field) for field in fields}


def _node_span(name: str) -> dict[str, list[str]]:
    return {"trace_spans": [name]}


def _curator_node(state: AnalysisGraphState) -> dict[str, Any]:
    try:
        next_state = run_curator(_agent_state(state))
        return {**_patch_from_agent(next_state, "curator"), **_node_span("curator")}
    except Exception as exc:
        return {
            "worker_errors": [f"curator: {exc.__class__.__name__}: {exc}"],
            **_node_span("curator"),
        }

def _classifier_node(state: AnalysisGraphState) -> dict[str, Any]:
    next_state = run_request_classifier(_agent_state(state))
    request = next_state.user_request
    route = {
        "analysis_scope": request.analysis_scope if request else None,
        "urgency_reason": request.urgency_reason if request else None,
        "requested_depth": request.requested_depth if request else "summary",
        "summary_only": bool(request and request.requested_depth == "summary"),
        "worker_plan": _worker_plan(next_state),
    }
    return {
        **_patch_from_agent(next_state, "user_request"),
        "graph_route": route,
        "trace_spans": ["classifier", "worker_fanout"],
    }


def _worker_plan(state: AgentState) -> list[str]:
    """
    worker_plan 결정 — single_stock도 업종 확인 시 macro 포함
    근거: 개별 종목도 업종 거시경제 환경에 직접 영향받음
    """
    scope = state.user_request.analysis_scope if state.user_request else None
    workers = ["quant", "qual", "competitor"]
    # single_stock도 업종이 확인되면 macro 분석 포함
    # 근거: 개별 종목도 업종 거시경제 환경에 직접 영향받음
    has_sector = bool(state.curator and state.curator.sector)
    if scope in {"portfolio", "sector"} or (scope == "single_stock" and has_sector):
        workers.append("macro")
    return workers


def _safe_worker_node(
    name: str,
    runner: Callable[[AgentState], AgentState],
    *fields: str,
) -> Callable[[AnalysisGraphState], dict[str, Any]]:
    def _node(state: AnalysisGraphState) -> dict[str, Any]:
        try:
            next_state = runner(_agent_state(state))
            return {**_patch_from_agent(next_state, *fields), **_node_span(name)}
        except Exception as exc:
            return {
                "worker_errors": [f"{name}: {exc.__class__.__name__}: {exc}"],
                **_node_span(name),
            }

    return _node


# ==========================================
# Send API fan-out 라우터
# classifier 이후 worker_plan 기반으로
# 각 worker 노드에 Send 메시지를 병렬 발송
# ==========================================
def _fanout_workers(state: AnalysisGraphState) -> list[Send]:
    """
    LangGraph Send API 기반 동적 fan-out.
    worker_plan에 있는 에이전트만 병렬 실행.
    macro는 업종 확인 시에만 포함됨.
    """
    plan = (state.get("graph_route") or {}).get("worker_plan") or [
        "quant", "qual", "competitor"
    ]
    return [Send(worker, state) for worker in plan]


def _quant_node(state: AnalysisGraphState) -> dict[str, Any]:
    return _safe_worker_node("quant", run_quant, "quant")(state)


def _qual_node(state: AnalysisGraphState) -> dict[str, Any]:
    return _safe_worker_node("qual", run_qual, "qual")(state)


def _competitor_node(state: AnalysisGraphState) -> dict[str, Any]:
    return _safe_worker_node("competitor", run_competitor, "competitor")(state)


def _macro_node(state: AnalysisGraphState) -> dict[str, Any]:
    """
    Macro Agent 노드.
    Send API fan-out으로 worker_plan에 있을 때만 호출되므로
    내부 스킵 로직 불필요.
    """
    return _safe_worker_node("macro", run_macro, "macro")(state)


def _strategist_node(state: AnalysisGraphState) -> dict[str, Any]:
    try:
        next_state = run_strategist(_agent_state(state))
    except Exception as exc:
        fallback = StrategistResult(
            signal="HOLD",
            confidence=30,
            suitability=30,
            headline="[부분 분석] 핵심 분석 결과가 부족해 보수적인 보유 검토로 제한합니다.",
            key_reasons=["분석 워커 실패로 충분한 근거를 확보하지 못했습니다."],
            risks=[
                f"Strategist 합성 실패로 conservative fallback을 사용했습니다: {exc.__class__.__name__}: {exc}"
            ],
            next_actions=["데이터 연결 상태를 확인한 뒤 분석을 다시 실행합니다."],
            degraded=True,
            contributing_agents=[],
            model_provider="fallback",
            model="conservative-rule",
            fallback_used=True,
        )
        return {"strategist": fallback, "worker_errors": [f"strategist: {exc}"], **_node_span("strategist")}

    strategist = next_state.strategist
    if strategist is not None and state.get("worker_errors"):
        strategist = strategist.model_copy(
            update={
                "degraded": True,
                "risks": [
                    *strategist.risks,
                    "일부 분석 노드 실패: " + " / ".join(state.get("worker_errors") or []),
                ],
            }
        )
    return {"strategist": strategist, **_node_span("strategist")}


def _investment_analyst_node(state: AnalysisGraphState) -> dict[str, Any]:
    next_state = run_investment_analyst(_agent_state(state))
    return {**_patch_from_agent(next_state, "strategist"), **_node_span("investment_analyst")}


def _guardrail_node(state: AnalysisGraphState) -> dict[str, Any]:
    try:
        next_state = run_guardrail(_agent_state(state))
        return {**_patch_from_agent(next_state, "guardrail"), **_node_span("guardrail")}
    except Exception as exc:  # pragma: no cover - defensive path
        strategist = state.get("strategist")
        return {
            "guardrail": GuardrailResult(
                passed=False,
                warnings=[f"Guardrail failed with exception: {exc.__class__.__name__}: {exc}"],
                revised_headline=(strategist.headline if strategist else "") or "",
                disclaimer="Guardrail evaluation failed; 일부 출력이 제한될 수 있습니다.",
                needs_revision=True,
                risk_level="high",
                checks=[
                    {
                        "name": "guardrail_exception",
                        "passed": False,
                        "severity": "block",
                        "detail": exc.__class__.__name__,
                    }
                ],
            ),
            **_node_span("guardrail"),
        }


def _apply_guardrail_node(state: AnalysisGraphState) -> dict[str, Any]:
    strategist = state.get("strategist")
    guardrail = state.get("guardrail")

    if strategist is None or guardrail is None:
        return _node_span("guardrail_apply")

    # =========================
    # 1. guardrail 실패 처리
    # =========================
    if not guardrail.passed:
        is_pii = (
            any("PII" in w for w in guardrail.warnings)
            or "@" in (strategist.headline or "")
        )

        if is_pii:
            fallback_headline = "민감 콘텐츠가 포함되어 일부 결과가 제한되었습니다."

            strategist = strategist.model_copy(
                update={
                    "headline": fallback_headline,
                    "signal": "HOLD",
                    "confidence": max(0, strategist.confidence - 30),
                    "suitability": max(0, strategist.suitability - 30),
                    "degraded": True,
                }
            )

            guardrail = guardrail.model_copy(
                update={"revised_headline": fallback_headline, "needs_revision": False}
            )

            return {
                "strategist": strategist,
                "guardrail": guardrail,
                **_node_span("guardrail_apply"),
            }

    # =========================
    # 2. revision loop
    # =========================
    needs_revision = bool(guardrail.needs_revision)
    if needs_revision:
        try:
            from stock_agent.agents.recomposer import run_recomposer

            max_retries = 2
            attempt = 0
            last_guardrail = guardrail
            last_strategist = strategist

            while attempt < max_retries and (last_guardrail.needs_revision or not last_guardrail.passed):
                attempt += 1

                patched = run_recomposer(
                    _agent_state({
                        **state,
                        "strategist": last_strategist,
                        "guardrail": last_guardrail,
                    })
                )

                patched = run_strategist(patched)
                last_strategist = patched.strategist

                try:
                    patched = run_investment_analyst(patched)
                except Exception:
                    pass

                patched = run_guardrail(patched)
                last_guardrail = patched.guardrail

            strategist = last_strategist
            guardrail = last_guardrail

        except Exception as exc:
            err = f"recomposition_loop_failed: {exc.__class__.__name__}: {exc}"
            return {"worker_errors": [err], **_node_span("guardrail_apply")}

    return {
        "strategist": strategist,
        "guardrail": guardrail,
        **_node_span("guardrail_apply"),
    }

def _renderer_node(state: AnalysisGraphState) -> dict[str, Any]:
    try:
        next_state = run_result_renderer(_agent_state(state))
        return {**_patch_from_agent(next_state, "rendered_report"), **_node_span("renderer")}
    except Exception as exc:
        return {"worker_errors": [f"renderer: {exc.__class__.__name__}: {exc}"], **_node_span("renderer")}


def build_analysis_graph():
    """
    LangGraph StateGraph 빌드.

    핵심 변경: Send API fan-out 적용
    - 기존: _route_workers → conditional_edges (4개 고정 라우팅)
    - 변경: _fanout_workers → Send API (worker_plan 기반 동적 병렬 실행)

    효과:
    - macro가 worker_plan에 없으면 실행 자체를 안 함 (스킵 로직 불필요)
    - quant/qual/competitor/macro 진짜 병렬 실행
    - strategist는 실행된 worker가 모두 끝난 후 join
    """
    graph = StateGraph(AnalysisGraphState)

    # 노드 등록
    graph.add_node("curator", _curator_node)
    graph.add_node("classifier", _classifier_node)
    graph.add_node("quant", _quant_node)
    graph.add_node("qual", _qual_node)
    graph.add_node("competitor", _competitor_node)
    graph.add_node("macro", _macro_node)
    graph.add_node("strategist", _strategist_node)
    graph.add_node("investment_analyst", _investment_analyst_node)
    graph.add_node("guardrail", _guardrail_node)
    graph.add_node("guardrail_apply", _apply_guardrail_node)
    graph.add_node("renderer", _renderer_node)

    # 엣지 연결
    graph.add_edge(START, "curator")
    graph.add_edge("curator", "classifier")

    # ── Send API fan-out ──────────────────────────────────────
    # classifier → worker_plan 기반 동적 병렬 실행
    # macro는 업종 확인 시에만 Send 발송 → 실행됨
    graph.add_conditional_edges("classifier", _fanout_workers)

    # worker들이 끝나면 strategist로 join
    graph.add_edge("quant", "strategist")
    graph.add_edge("qual", "strategist")
    graph.add_edge("competitor", "strategist")
    graph.add_edge("macro", "strategist")

    graph.add_edge("strategist", "investment_analyst")
    graph.add_edge("investment_analyst", "guardrail")
    graph.add_edge("guardrail", "guardrail_apply")
    graph.add_edge("guardrail_apply", "renderer")
    graph.add_edge("renderer", END)

    return graph.compile()


def _initial_state(user_query: str, user_profile: UserProfile, portfolio: Portfolio) -> AnalysisGraphState:
    return {
        "user_query": user_query,
        "user_request": UserRequest(raw_query=user_query),
        "user_profile": user_profile,
        "portfolio": portfolio,
        "as_of_date": "2026-05-21",
        "graph_route": {},
        "trace_spans": [],
        "worker_errors": [],
    }


def _merge_graph_update(
    state: AnalysisGraphState,
    node_name: str,
    patch: dict[str, Any],
) -> AnalysisGraphState:
    merged = dict(state)
    for key, value in patch.items():
        if key in {"trace_spans", "worker_errors"}:
            merged[key] = [*(merged.get(key) or []), *value]
        elif key == "graph_route":
            merged[key] = {**(merged.get(key) or {}), **value}
        else:
            merged[key] = value
    return merged


def _event_status(node_name: str, patch: dict[str, Any]) -> str:
    if any(error.startswith(f"{node_name}:") for error in patch.get("worker_errors", [])):
        return "error"
    return "done"


def _event_detail(node_name: str, state: AnalysisGraphState, patch: dict[str, Any]) -> str:
    if patch.get("worker_errors"):
        return " / ".join(patch["worker_errors"])
    if node_name == "classifier":
        request = patch.get("user_request")
        if request is None:
            return "분류 결과 없음"
        return (
            f"{request.analysis_scope or 'unknown'} route, "
            f"{request.urgency_reason or 'general'}, {request.requested_depth}"
        )
    if node_name == "investment_analyst":
        strategist = patch.get("strategist")
        if strategist is None:
            return ""
        return f"{strategist.model_provider}/{strategist.model}, fallback={strategist.fallback_used}"
    if node_name == "guardrail":
        guardrail = patch.get("guardrail")
        if guardrail is None:
            return ""
        return f"passed={guardrail.passed}, risk={guardrail.risk_level}"
    if node_name in {"quant", "qual", "competitor", "macro"}:
        result = patch.get(node_name)
        score = getattr(result, "score", None)
        fallback = False
        for attr in ("reasons", "evidence", "risks", "warnings", "data_quality_flags"):
            values = getattr(result, attr, []) or []
            fallback = fallback or any(
                marker in str(value).lower()
                for value in values
                for marker in ("fallback", "mock")
            )
        detail = f"score={score}" if score is not None else ""
        if fallback:
            detail = f"{detail}, fallback/mock 포함" if detail else "fallback/mock 포함"
        return detail
    if node_name == "strategist":
        strategist = patch.get("strategist")
        if strategist is None:
            return ""
        return (
            f"{strategist.signal}, confidence={strategist.confidence}, "
            f"degraded={strategist.degraded}"
        )
    return ""


def stream_phase1_analysis_events(
    user_query: str,
    user_profile: UserProfile | None = None,
    portfolio: Portfolio | None = None,
):
    if user_profile is None or portfolio is None:
        demo_profile, demo_portfolio = build_demo_profile()
        user_profile = user_profile or demo_profile
        portfolio = portfolio or demo_portfolio

    graph = build_analysis_graph()
    state = _initial_state(user_query, user_profile, portfolio)
    for chunk in graph.stream(state):
        for node_name, patch in chunk.items():
            state = _merge_graph_update(state, node_name, patch)
            yield {
                "type": "node",
                "node": node_name,
                "label": _EVENT_LABELS.get(node_name, node_name),
                "status": _event_status(node_name, patch),
                "detail": _event_detail(node_name, state, patch),
                "state": _agent_state(state),
            }

    output = _to_output(_agent_state(state))
    yield {
        "type": "complete",
        "node": "complete",
        "label": "Complete",
        "status": "done",
        "detail": "분석 완료",
        "output": output,
        "state": output.state,
    }


def _tier_items(items: list[str], state: AgentState) -> list[str]:
    if state.user_request and state.user_request.requested_depth == "summary":
        return items[:1]
    return items


def _to_output(state: AgentState) -> AnalysisOutput:
    if state.strategist is None or state.guardrail is None:
        raise RuntimeError("analysis pipeline finished without strategist or guardrail output")

    # guardrail 기반 보정
    is_blocked = not state.guardrail.passed

    tier1 = Tier1Result(
        signal="HOLD" if is_blocked else state.strategist.signal,
        confidence=max(0, state.strategist.confidence - (30 if is_blocked else 0)),
        suitability=max(0, state.strategist.suitability - (30 if is_blocked else 0)),
        headline=state.guardrail.revised_headline,
        disclaimer=state.guardrail.disclaimer,
    )

    return AnalysisOutput(
        tier1=tier1,
        tier2={
            "정량 근거": _tier_items(state.quant.reasons if state.quant else [], state),
            "정성 근거": _tier_items(state.qual.evidence if state.qual else [], state),
            "Peer 비교": _tier_items(state.competitor.evidence if state.competitor else [], state),
            "거시경제": _tier_items(state.macro.reasons if state.macro else [], state),
            "포트폴리오 적합도": state.strategist.next_actions,
            "리스크": state.strategist.risks,
        },
        tier3={
            "PB 리포트": "PDF 다운로드 가능",
            "밸류에이션 Excel": "Excel 다운로드 가능",
            "산업/뉴스 분석 HTML": "HTML 다운로드 가능",
        },
        state=state,
    )


def run_phase1_analysis(
    user_query: str,
    user_profile: UserProfile | None = None,
    portfolio: Portfolio | None = None,
) -> AnalysisOutput:
    if user_profile is None or portfolio is None:
        demo_profile, demo_portfolio = build_demo_profile()
        user_profile = user_profile or demo_profile
        portfolio = portfolio or demo_portfolio

    output: AnalysisOutput | None = None
    for event in stream_phase1_analysis_events(user_query, user_profile, portfolio):
        if event["type"] == "complete":
            output = event["output"]
    if output is None:
        raise RuntimeError("analysis pipeline did not produce output")
    return output
