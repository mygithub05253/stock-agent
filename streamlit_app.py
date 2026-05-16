import streamlit as st

from stock_agent.graph import build_demo_profile, run_phase1_analysis
from stock_agent.schemas import Portfolio, UserProfile


def _signal_badge(signal: str) -> str:
    colors = {"BUY": "#0f766e", "HOLD": "#b45309", "SELL": "#b91c1c"}
    return (
        f"<span style='background:{colors.get(signal, '#334155')}; color:white; "
        "padding:0.25rem 0.55rem; border-radius:0.35rem; font-weight:700;'>"
        f"{signal}</span>"
    )


def main() -> None:
    st.set_page_config(
        page_title="stock-agent - 포트폴리오 분석",
        page_icon="📊",
        layout="wide",
    )

    demo_profile, demo_portfolio = build_demo_profile()

    with st.sidebar:
        st.subheader("MVP 사용자 데이터")
        risk_label = st.selectbox(
            "위험 감내도",
            options=["medium", "low", "high"],
            format_func={"low": "낮음", "medium": "보통", "high": "높음"}.get,
        )
        horizon = st.slider("투자 기간(개월)", min_value=1, max_value=36, value=12)
        cash_weight = st.slider("현금 비중", min_value=0, max_value=100, value=20) / 100

        st.caption("Phase 1에서는 회원가입 없이 목 프로필과 보유 종목으로 E2E를 검증합니다.")
        st.write("보유 종목")
        for holding in demo_portfolio.holdings:
            st.write(f"- {holding.corp_name} {holding.weight:.0%}")

    user_profile = UserProfile(
        user_id=demo_profile.user_id,
        risk_tolerance=risk_label,
        investment_horizon_months=horizon,
        cash_source=demo_profile.cash_source,
        preferred_sectors=demo_profile.preferred_sectors,
    )
    portfolio = Portfolio(holdings=demo_portfolio.holdings, cash_weight=cash_weight)

    st.title("국내 주식 포트폴리오 분석")
    st.caption("Curator -> Quant/Qual/Competitor -> Strategist -> Guardrail")

    query = st.text_input(
        "질문",
        value="내 포트폴리오에서 삼성전자 어떻게 할까?",
        placeholder="예: 내 포트폴리오에서 삼성전자 어떻게 할까?",
    )

    if st.button("분석 실행", type="primary", use_container_width=False):
        with st.spinner("에이전트 파이프라인 실행 중..."):
            output = run_phase1_analysis(query, user_profile=user_profile, portfolio=portfolio)
        st.session_state["analysis_output"] = output

    output = st.session_state.get("analysis_output")
    if output is None:
        st.info("분석 실행을 누르면 Phase 1 mock 파이프라인 결과가 표시됩니다.")
        return

    tier1 = output.tier1
    st.divider()
    st.subheader("Tier 1. 한 줄 결론")
    col_signal, col_confidence, col_suitability = st.columns(3)
    col_signal.markdown(_signal_badge(tier1.signal), unsafe_allow_html=True)
    col_confidence.metric("신뢰도", f"{tier1.confidence}%")
    col_suitability.metric("포트폴리오 적합도", f"{tier1.suitability}%")
    st.markdown(f"### {tier1.headline}")
    st.caption(tier1.disclaimer)

    st.subheader("Tier 2. 핵심 근거")
    tabs = st.tabs(["정량", "정성", "Peer", "적합도", "리스크"])
    for tab, key in zip(tabs, ["정량 근거", "정성 근거", "Peer 비교", "포트폴리오 적합도", "리스크"], strict=True):
        with tab:
            for item in output.tier2.get(key, []):
                st.write(f"- {item}")

    with st.expander("Phase 1 상세 상태 보기"):
        st.json(output.model_dump(mode="json"), expanded=False)


if __name__ == "__main__":
    main()
