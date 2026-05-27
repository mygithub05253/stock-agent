import streamlit as st

from stock_agent.graph import run_phase1_analysis
from stock_agent.intake import (
    build_portfolio_from_text,
    get_onboarding_card,
    infer_user_profile,
    onboarding_card_count,
)
from stock_agent.schemas import Portfolio, UserProfile


def _signal_badge(signal: str) -> str:
    colors = {"BUY": "#0f766e", "HOLD": "#b45309", "SELL": "#b91c1c"}
    return (
        f"<span style='background:{colors.get(signal, '#334155')}; color:white; "
        "padding:0.25rem 0.55rem; border-radius:0.35rem; font-weight:700;'>"
        f"{signal}</span>"
    )


def _init_intake_state() -> None:
    st.session_state.setdefault("intake_stage", "onboarding")
    st.session_state.setdefault("onboarding_step", 0)
    st.session_state.setdefault("onboarding_answers", {})
    st.session_state.setdefault("inferred_profile", None)
    st.session_state.setdefault("holdings_text", "삼성전자 10주, SK하이닉스 3주")
    st.session_state.setdefault("cash_weight", 0.2)
    st.session_state.setdefault("intake_portfolio", None)
    st.session_state.setdefault("intake_messages", [])


def _reset_intake() -> None:
    for key in [
        "intake_stage",
        "onboarding_step",
        "onboarding_answers",
        "inferred_profile",
        "holdings_text",
        "cash_weight",
        "intake_portfolio",
        "analysis_output",
        "intake_messages",
    ]:
        st.session_state.pop(key, None)
    _init_intake_state()


def _format_risk_label(risk_tolerance: str) -> str:
    return {"low": "안정형", "medium": "중립형", "high": "공격형"}.get(
        risk_tolerance,
        risk_tolerance,
    )


def _render_onboarding_step() -> None:
    total_steps = onboarding_card_count()
    step = st.session_state["onboarding_step"]
    card = get_onboarding_card(step)
    answers = st.session_state["onboarding_answers"]

    st.subheader(f"1. 투자 성향 질문 {step + 1}/{total_steps}")
    st.progress((step + 1) / total_steps)
    st.markdown(f"### {card['question']}")

    options = card["options"]
    labels = [option["label"] for option in options]
    current_value = answers.get(card["id"])
    current_index = 0
    if current_value is not None:
        for index, option in enumerate(options):
            if option["value"] == current_value:
                current_index = index
                break

    selected_label = st.radio(
        "답변을 선택해 주세요",
        options=labels,
        index=current_index,
        label_visibility="collapsed",
        key=f"onboarding_card_{card['id']}",
    )
    selected_option = options[labels.index(selected_label)]

    col_prev, col_next, col_reset = st.columns([1, 1, 1])
    with col_prev:
        if st.button("이전", disabled=step == 0):
            st.session_state["onboarding_step"] = max(0, step - 1)
            st.rerun()
    with col_next:
        next_label = "성향 분석" if step == total_steps - 1 else "다음"
        if st.button(next_label, type="primary"):
            answers[card["id"]] = selected_option["value"]
            st.session_state["onboarding_answers"] = answers
            if step == total_steps - 1:
                profile = infer_user_profile(answers)
                st.session_state["inferred_profile"] = profile.model_dump(mode="json")
                st.session_state["intake_stage"] = "portfolio"
            else:
                st.session_state["onboarding_step"] = step + 1
            st.rerun()
    with col_reset:
        if st.button("처음부터"):
            _reset_intake()
            st.rerun()


def _get_inferred_profile() -> UserProfile:
    profile_data = st.session_state.get("inferred_profile")
    if not profile_data:
        return infer_user_profile(st.session_state["onboarding_answers"])
    return UserProfile(**profile_data)


def _render_profile_summary(user_profile: UserProfile) -> None:
    st.subheader("2. 분석된 투자 성향")
    col_risk, col_horizon, col_loss = st.columns(3)
    col_risk.metric("투자성향", _format_risk_label(user_profile.risk_tolerance))
    col_horizon.metric("투자 기간", f"{user_profile.investment_horizon_months}개월")
    loss_label = (
        f"{user_profile.max_drawdown_tolerance:.0%}"
        if user_profile.max_drawdown_tolerance is not None
        else "미정"
    )
    col_loss.metric("손실 감내", loss_label)
    st.caption("투자성향은 답변 점수와 보정 룰로 추론한 값입니다.")


def _render_portfolio_step(user_profile: UserProfile) -> Portfolio | None:
    _render_profile_summary(user_profile)
    st.subheader("3. 보유 종목 입력")
    holdings_text = st.text_area(
        "보유 종목을 알려주세요",
        value=st.session_state["holdings_text"],
        placeholder="예: 삼성전자 10주, SK하이닉스 3주",
        height=90,
    )
    st.session_state["holdings_text"] = holdings_text

    cash_weight = st.slider(
        "현금 비중",
        min_value=0,
        max_value=100,
        value=round(st.session_state["cash_weight"] * 100),
    ) / 100
    st.session_state["cash_weight"] = cash_weight

    portfolio, warnings = build_portfolio_from_text(holdings_text, cash_weight=cash_weight)
    if warnings:
        for warning in warnings:
            st.warning(warning)

    if portfolio.holdings:
        _render_portfolio_summary(portfolio)
    else:
        st.info("예시처럼 `삼성전자 10주, SK하이닉스 3주` 형태로 입력해 주세요.")

    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("성향 질문으로 돌아가기"):
            st.session_state["intake_stage"] = "onboarding"
            st.rerun()
    with col_next:
        if st.button("포트폴리오 저장", type="primary", disabled=not portfolio.holdings):
            st.session_state["intake_portfolio"] = portfolio.model_dump(mode="json")
            st.session_state["intake_stage"] = "analysis"
            st.rerun()

    return portfolio


def _get_saved_portfolio() -> Portfolio | None:
    portfolio_data = st.session_state.get("intake_portfolio")
    if not portfolio_data:
        return None
    return Portfolio(**portfolio_data)


def _render_portfolio_summary(portfolio: Portfolio) -> None:
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


def _render_analysis_step(user_profile: UserProfile, portfolio: Portfolio) -> None:
    _render_profile_summary(user_profile)
    st.subheader("3. 저장된 포트폴리오")
    _render_portfolio_summary(portfolio)

    st.subheader("4. 질문 입력")
    query = st.text_input(
        "이제 궁금한 점을 질문해 주세요",
        value="삼성전자 급등했는데 안정형이면 어떻게 할까?",
        placeholder="예: SK하이닉스 비중 괜찮아?",
    )

    col_run, col_edit = st.columns([1, 1])
    with col_run:
        if st.button("분석 실행", type="primary"):
            st.session_state["intake_messages"].append({"role": "user", "content": query})
            with st.spinner("에이전트 파이프라인 실행 중..."):
                output = run_phase1_analysis(query, user_profile=user_profile, portfolio=portfolio)
            st.session_state["analysis_output"] = output
    with col_edit:
        if st.button("포트폴리오 다시 입력"):
            st.session_state["intake_stage"] = "portfolio"
            st.rerun()


def _render_output() -> None:
    output = st.session_state.get("analysis_output")
    if output is None:
        st.info("질문을 실행하면 분류 결과와 분석 결과가 표시됩니다.")
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
        page_title="stock-agent - 단계형 투자성향 수집",
        page_icon="📊",
        layout="wide",
    )
    _init_intake_state()

    st.title("단계형 투자성향 수집")
    st.caption("질문 카드에 하나씩 답하면 투자성향을 추론하고, 보유 종목을 받아 분석합니다.")

    stage = st.session_state["intake_stage"]
    if stage == "onboarding":
        _render_onboarding_step()
    elif stage == "portfolio":
        user_profile = _get_inferred_profile()
        _render_portfolio_step(user_profile)
    else:
        user_profile = _get_inferred_profile()
        portfolio = _get_saved_portfolio()
        if portfolio is None:
            st.session_state["intake_stage"] = "portfolio"
            st.rerun()
        _render_analysis_step(user_profile, portfolio)
        _render_output()


if __name__ == "__main__":
    main()
