import streamlit as st

from stock_agent.graph import run_phase1_analysis
from stock_agent.intake import build_portfolio_from_text
from stock_agent.schemas import Portfolio, UserProfile


_SECTOR_OPTIONS = ["반도체", "금융"]


def _signal_badge(signal: str) -> str:
    colors = {"BUY": "#0f766e", "HOLD": "#b45309", "SELL": "#b91c1c"}
    return (
        f"<span style='background:{colors.get(signal, '#334155')}; color:white; "
        "padding:0.25rem 0.55rem; border-radius:0.35rem; font-weight:700;'>"
        f"{signal}</span>"
    )


def _init_intake_state() -> None:
    st.session_state.setdefault(
        "intake_profile",
        {
            "risk_tolerance": "medium",
            "investment_horizon_months": 12,
            "target_return_rate": 0.1,
            "max_drawdown_tolerance": -0.1,
            "investment_goal": "growth",
            "experience_level": "beginner",
            "preferred_sectors": ["반도체"],
            "liquidity_need_level": "medium",
            "cash_weight": 0.2,
        },
    )
    st.session_state.setdefault("holdings_text", "삼성전자 10주, SK하이닉스 3주")
    st.session_state.setdefault("intake_messages", [])


def _build_user_profile() -> UserProfile:
    profile = st.session_state["intake_profile"]
    return UserProfile(
        user_id="session-user",
        risk_tolerance=profile["risk_tolerance"],
        investment_horizon_months=profile["investment_horizon_months"],
        target_return_rate=profile["target_return_rate"],
        max_drawdown_tolerance=profile["max_drawdown_tolerance"],
        investment_goal=profile["investment_goal"],
        experience_level=profile["experience_level"],
        preferred_sectors=profile["preferred_sectors"],
        liquidity_need_level=profile["liquidity_need_level"],
    )


def _render_profile_cards() -> None:
    profile = st.session_state["intake_profile"]

    st.subheader("1. 투자 성향 카드")
    col_risk, col_horizon = st.columns(2)
    with col_risk:
        profile["risk_tolerance"] = st.radio(
            "투자성향",
            options=["low", "medium", "high"],
            format_func={"low": "안정형", "medium": "중립형", "high": "공격형"}.get,
            horizontal=True,
        )
    with col_horizon:
        profile["investment_horizon_months"] = st.slider(
            "투자 기간(개월)",
            min_value=1,
            max_value=36,
            value=profile["investment_horizon_months"],
        )

    col_return, col_loss = st.columns(2)
    with col_return:
        profile["target_return_rate"] = (
            st.slider("목표 수익률", min_value=0, max_value=50, value=10) / 100
        )
    with col_loss:
        profile["max_drawdown_tolerance"] = (
            -st.slider("감내 가능한 손실률", min_value=0, max_value=50, value=10) / 100
        )

    col_goal, col_experience = st.columns(2)
    with col_goal:
        profile["investment_goal"] = st.selectbox(
            "투자 목적",
            options=["growth", "wealth_preservation", "short_term_profit", "dividend"],
            format_func={
                "growth": "중장기 성장",
                "wealth_preservation": "안정적 자산관리",
                "short_term_profit": "단기 수익",
                "dividend": "배당",
            }.get,
        )
    with col_experience:
        profile["experience_level"] = st.selectbox(
            "투자 경험",
            options=["beginner", "intermediate", "advanced"],
            format_func={"beginner": "초보", "intermediate": "중급", "advanced": "고급"}.get,
        )

    col_sector, col_cash = st.columns(2)
    with col_sector:
        profile["preferred_sectors"] = st.multiselect(
            "관심 산업",
            options=_SECTOR_OPTIONS,
            default=profile["preferred_sectors"],
        )
    with col_cash:
        profile["cash_weight"] = st.slider("현금 비중", min_value=0, max_value=100, value=20) / 100


def _render_portfolio_cards() -> tuple[Portfolio, list[str]]:
    st.subheader("2. 보유 종목 카드")
    holdings_text = st.text_area(
        "보유 종목을 알려주세요",
        value=st.session_state["holdings_text"],
        placeholder="예: 삼성전자 10주, SK하이닉스 3주",
        height=90,
    )
    st.session_state["holdings_text"] = holdings_text

    cash_weight = st.session_state["intake_profile"]["cash_weight"]
    portfolio, warnings = build_portfolio_from_text(holdings_text, cash_weight=cash_weight)

    if warnings:
        for warning in warnings:
            st.warning(warning)

    if not portfolio.holdings:
        st.info("예시처럼 `삼성전자 10주, SK하이닉스 3주` 형태로 입력해 주세요.")
        return portfolio, warnings

    st.write("포트폴리오 요약")
    total_value = portfolio.total_market_value or 0
    col_total, col_cash = st.columns(2)
    col_total.metric("총 평가금액", f"{total_value:,}원")
    col_cash.metric("현금 비중", f"{portfolio.cash_weight:.0%}")

    for holding in portfolio.holdings:
        weight_label = f"{holding.weight:.0%}" if holding.weight is not None else "계산 불가"
        market_value = holding.market_value or 0
        st.write(f"- {holding.corp_name}: {holding.qty}주 / {market_value:,}원 / {weight_label}")

    sector_weights = portfolio.sector_weights()
    if sector_weights:
        st.write("섹터 비중")
        for sector, weight in sector_weights.items():
            st.progress(weight, text=f"{sector} {weight:.0%}")

    return portfolio, warnings


def _render_analysis_cards(user_profile: UserProfile, portfolio: Portfolio) -> None:
    st.subheader("3. 질문 카드")
    query = st.text_input(
        "이제 궁금한 점을 질문해 주세요",
        value="삼성전자 급등했는데 안정형이면 어떻게 할까?",
        placeholder="예: SK하이닉스 비중 괜찮아?",
    )

    validation_errors: list[str] = []
    if not user_profile.preferred_sectors:
        validation_errors.append("관심 산업을 1개 이상 선택해 주세요.")
    if not portfolio.holdings:
        validation_errors.append("보유 종목을 1개 이상 입력해 주세요.")

    if validation_errors:
        for error in validation_errors:
            st.error(error)

    if st.button("분석 실행", type="primary", disabled=bool(validation_errors)):
        st.session_state["intake_messages"].append({"role": "user", "content": query})
        with st.spinner("에이전트 파이프라인 실행 중..."):
            output = run_phase1_analysis(query, user_profile=user_profile, portfolio=portfolio)
        st.session_state["analysis_output"] = output


def _render_output() -> None:
    output = st.session_state.get("analysis_output")
    if output is None:
        st.info("투자성향과 보유 종목을 입력한 뒤 질문을 실행해 보세요.")
        return

    tier1 = output.tier1
    st.divider()
    st.subheader("분석 결과")
    col_signal, col_confidence, col_suitability = st.columns(3)
    col_signal.markdown(_signal_badge(tier1.signal), unsafe_allow_html=True)
    col_confidence.metric("신뢰도", f"{tier1.confidence}%")
    col_suitability.metric("포트폴리오 적합도", f"{tier1.suitability}%")
    st.markdown(f"### {tier1.headline}")
    st.caption(tier1.disclaimer)

    if output.state.user_request:
        st.write("질문 분류")
        st.json(output.state.user_request.model_dump(mode="json"), expanded=False)

    tabs = st.tabs(["정량", "정성", "Peer", "적합도", "리스크"])
    for tab, key in zip(tabs, ["정량 근거", "정성 근거", "Peer 비교", "포트폴리오 적합도", "리스크"], strict=True):
        with tab:
            for item in output.tier2.get(key, []):
                st.write(f"- {item}")

    with st.expander("상세 상태 보기"):
        st.json(output.model_dump(mode="json"), expanded=False)


def main() -> None:
    st.set_page_config(
        page_title="stock-agent - 대화형 포트폴리오 수집",
        page_icon="📊",
        layout="wide",
    )
    _init_intake_state()

    st.title("대화형 포트폴리오 수집")
    st.caption("카드형 질문으로 투자성향과 보유 종목을 모은 뒤, 질문을 분류해 분석합니다.")

    _render_profile_cards()
    portfolio, _ = _render_portfolio_cards()
    user_profile = _build_user_profile()
    _render_analysis_cards(user_profile, portfolio)
    _render_output()


if __name__ == "__main__":
    main()
