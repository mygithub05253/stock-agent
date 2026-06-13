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
)
from stock_agent.schemas.analysis import (
    AgentState,
    AnalysisOutput,
    Holding,
    Portfolio,
    Tier1Result,
    UserProfile,
    UserRequest,
)


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


def run_phase1_analysis(
    user_query: str,
    user_profile: UserProfile | None = None,
    portfolio: Portfolio | None = None,
) -> AnalysisOutput:
    if user_profile is None or portfolio is None:
        demo_profile, demo_portfolio = build_demo_profile()
        user_profile = user_profile or demo_profile
        portfolio = portfolio or demo_portfolio

    state = AgentState(
        user_query=user_query,
        user_request=UserRequest(raw_query=user_query),
        user_profile=user_profile,
        portfolio=portfolio,
    )
    state = run_curator(state)
    state.as_of_date = "2026-05-21"
    state = run_request_classifier(state)

    # Phase 1 uses local mock workers. The contract mirrors the future LangGraph
    # fan-out: Quant, Qual, and Competitor only depend on Curator output.
    state = run_quant(state)
    state = run_qual(state)
    state = run_competitor(state)
    state = run_macro(state)
    state = run_strategist(state)
    state = run_investment_analyst(state)
    # Guardrail is critical but must not crash the pipeline; capture exceptions.
    try:
        state = run_guardrail(state)
    except Exception as exc:  # pragma: no cover - defensive path
        # populate a conservative GuardrailResult on failure
        from stock_agent.schemas.analysis import GuardrailResult

        state.guardrail = GuardrailResult(
            passed=False,
            warnings=[f"Guardrail failed with exception: {exc.__class__.__name__}: {exc}"],
            revised_headline=(state.strategist.headline if state.strategist else "") or "",
            disclaimer="Guardrail evaluation failed; 일부 출력이 제한될 수 있습니다.",
        )

    # If guardrail softening/guarantee issues were detected, attempt an automatic rewrite
    # up to a small number of retries to see if the content can be safely softened.
    from stock_agent.agents import guardrail as guardrail_module

    max_rewrites = 2
    rewrite_attempts = 0
    if state.guardrail and state.strategist:
        gw = state.guardrail
        # determine whether it's worth attempting an automatic rewrite
        while rewrite_attempts < max_rewrites and not gw.passed and any(
            kw in w.lower() for w in gw.warnings for kw in ("guarantee", "soften", "insufficient")
        ):
            rewrite_attempts += 1
            # perform a conservative rewrite of the headline and re-evaluate
            try:
                strat = state.strategist
                new_headline = guardrail_module._soften_headline(strat.headline or "")
                strat.headline = new_headline
                state = run_guardrail(state)
                gw = state.guardrail
                if gw.passed:
                    break
            except Exception:
                break

    # Apply Guardrail decisions to strategist output: soften or redact as needed
    if state.guardrail and state.strategist:
        gw = state.guardrail
        strat = state.strategist
        if not gw.passed:
            # If PII or profanity detected, redact and downgrade signal
            if any("PII" in w or "Inappropriate language" in w for w in gw.warnings):
                strat.headline = "출력 제한: 민감 콘텐츠가 검출되어 일부 내용이 숨겨졌습니다."
                strat.signal = "HOLD"
                strat.confidence = max(0, strat.confidence - 30)
                strat.suitability = max(0, strat.suitability - 30)
                # reflect redact in guardrail revised_headline as well
                gw.revised_headline = strat.headline
            else:
                # Otherwise, adopt the guardrail-revised headline (softened)
                strat.headline = gw.revised_headline

    if state.strategist is None or state.guardrail is None:
        raise RuntimeError("analysis pipeline finished without strategist or guardrail output")

    tier1 = Tier1Result(
        signal=state.strategist.signal,
        confidence=state.strategist.confidence,
        suitability=state.strategist.suitability,
        headline=state.guardrail.revised_headline,
        disclaimer=state.guardrail.disclaimer,
    )

    return AnalysisOutput(
        tier1=tier1,
        tier2={
            "정량 근거": state.quant.reasons if state.quant else [],
            "정성 근거": state.qual.evidence if state.qual else [],
            "Peer 비교": state.competitor.evidence if state.competitor else [],
            "포트폴리오 적합도": state.strategist.next_actions,
            "리스크": state.strategist.risks,
        },
        tier3={
            "PB 리포트": "Phase 5에서 PDF/DOCX 생성 예정",
            "밸류에이션 Excel": "Phase 5에서 Excel 생성 예정",
            "산업/뉴스 분석 HTML": "Phase 3 RAG 연결 후 생성 예정",
        },
        state=state,
    )
