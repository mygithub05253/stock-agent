from stock_agent.agents import (
    run_competitor,
    run_curator,
    run_guardrail,
    run_qual,
    run_quant,
    run_strategist,
)
from stock_agent.schemas.analysis import (
    AgentState,
    AnalysisOutput,
    Holding,
    Portfolio,
    Tier1Result,
    UserProfile,
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
                Holding(stock_code="005930", corp_name="삼성전자", weight=0.32, avg_price=72000),
                Holding(stock_code="000660", corp_name="SK하이닉스", weight=0.18, avg_price=185000),
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

    state = AgentState(user_query=user_query, user_profile=user_profile, portfolio=portfolio)
    state = run_curator(state)

    # Phase 1 uses local mock workers. The contract mirrors the future LangGraph
    # fan-out: Quant, Qual, and Competitor only depend on Curator output.
    state = run_quant(state)
    state = run_qual(state)
    state = run_competitor(state)
    state = run_strategist(state)
    state = run_guardrail(state)

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
