import streamlit as st

from stock_agent.graph import run_phase1_analysis
from stock_agent.intake import (
    STOCK_CATALOG,
    build_holding_from_selection,
    build_holding_weights,
    get_stock_options,
    get_onboarding_card,
    infer_user_profile,
    onboarding_card_count,
)
from stock_agent.schemas import Portfolio, UserProfile


_DEFAULT_QTY_BY_CORP = {
    "SK하이닉스": 2,
    "삼성전자": 3,
    "한미반도체": 2,
    "KB금융": 5,
    "신한지주": 5,
}


_DEFAULT_AVG_PRICE_RATIO_BY_CORP = {
    "SK하이닉스": 0.92,
    "삼성전자": 0.95,
    "한미반도체": 0.9,
    "KB금융": 0.94,
    "신한지주": 0.96,
}


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
    st.session_state.setdefault("cash_amount", 0)
    st.session_state.setdefault("intake_messages", [])


def _reset_intake() -> None:
    for key in [
        "intake_stage",
        "onboarding_step",
        "onboarding_answers",
        "inferred_profile",
        "cash_amount",
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
    st.subheader("2. 투자 성향 분석 에이전트 결과")
    col_risk, col_horizon, col_loss = st.columns(3)
    col_risk.metric("투자성향", _format_risk_label(user_profile.risk_tolerance))
    col_horizon.metric("투자 기간", f"{user_profile.investment_horizon_months}개월")
    loss_label = (
        f"{user_profile.max_drawdown_tolerance:.0%}"
        if user_profile.max_drawdown_tolerance is not None
        else "미정"
    )
    col_loss.metric("손실 감내", loss_label)
    with st.status("InvestorProfile Agent 완료", state="complete", expanded=False):
        st.write("온보딩 답변 점수화")
        st.write("투자 기간, 손실 감내, 유동성 필요도 보정")
        st.write("최종 투자성향과 목표수익률 산출")


def _render_portfolio_step(user_profile: UserProfile) -> Portfolio | None:
    _render_profile_summary(user_profile)
    st.subheader("3. 보유 종목 입력")
    st.caption("후보 산업을 고르면 시가총액 상위 후보 10개 안에서 종목을 선택할 수 있습니다.")

    selected_sectors = st.multiselect(
        "후보 산업",
        options=["반도체", "금융"],
        default=user_profile.preferred_sectors or ["반도체", "금융"],
    )
    if not selected_sectors:
        selected_sectors = ["반도체", "금융"]
        st.info("후보 산업을 최소 1개 이상 선택해야 해서 전체 후보를 보여줍니다.")

    stock_names = get_stock_options(selected_sectors, limit=10)

    selected_holdings = []
    st.write("보유 종목")
    for row_start in range(0, len(stock_names), 2):
        row_columns = st.columns(2, gap="medium")
        for column, corp_name in zip(row_columns, stock_names[row_start : row_start + 2], strict=False):
            with column:
                current_price = int(STOCK_CATALOG[corp_name]["current_price"])
                default_avg_price = int(
                    current_price * _DEFAULT_AVG_PRICE_RATIO_BY_CORP.get(corp_name, 1.0)
                )
                name_col, qty_col, price_col = st.columns([1.35, 0.75, 1])
                with name_col:
                    st.markdown(f"**{corp_name}**")
                    st.caption(f"현재가 {current_price:,}원")
                with qty_col:
                    qty = st.number_input(
                        f"{corp_name} 수량",
                        min_value=0,
                        value=_DEFAULT_QTY_BY_CORP.get(corp_name, 0),
                        step=1,
                        label_visibility="visible",
                        key=f"stock_qty_{corp_name}",
                    )
                with price_col:
                    avg_price = st.number_input(
                        f"{corp_name} 평단가",
                        min_value=0,
                        value=default_avg_price,
                        step=1000,
                        format="%d",
                        label_visibility="visible",
                        key=f"stock_avg_price_{corp_name}",
                    )
                if qty > 0:
                    selected_holdings.append(
                        build_holding_from_selection(corp_name, int(qty), avg_price=int(avg_price))
                    )

    holdings_value = sum(holding.market_value or 0 for holding in selected_holdings)
    cash_amount = st.number_input(
        "보유 현금",
        min_value=0,
        value=st.session_state["cash_amount"],
        step=100000,
        format="%d",
    )
    st.session_state["cash_amount"] = int(cash_amount)
    total_assets = holdings_value + int(cash_amount)
    cash_weight = int(cash_amount) / total_assets if total_assets > 0 else 0

    portfolio = Portfolio(
        holdings=build_holding_weights(selected_holdings),
        cash_weight=cash_weight,
    )
    if portfolio.holdings:
        _render_portfolio_summary(portfolio)
    else:
        st.info("보유 종목을 1개 이상 선택해 주세요.")

    if portfolio.holdings:
        st.subheader("4. 대화형 질문")
        st.info("이제 바로 질문할 수 있습니다. 아래 입력창에 궁금한 종목이나 상황을 적어 주세요.")
        if st.session_state["intake_messages"]:
            for message in st.session_state["intake_messages"]:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

        analysis_targets = _analysis_target_options(portfolio)
        selected_target = st.selectbox(
            "분석 대상 선택",
            options=analysis_targets,
            index=0,
            key="analysis_target",
        )
        default_query = _default_analysis_query(selected_target, portfolio)
        if st.session_state.get("analysis_query_target") != selected_target:
            st.session_state["analysis_query"] = default_query
            st.session_state["analysis_query_target"] = selected_target

        query = st.text_input(
            "궁금한 점을 입력해 주세요",
            value=default_query,
            placeholder="예: SK하이닉스 비중 괜찮아?",
            key="analysis_query",
        )

        col_run, col_edit = st.columns([1, 1])
        with col_run:
            if st.button("분석 실행", type="primary"):
                st.session_state["intake_messages"] = [{"role": "user", "content": query}]
                with st.spinner("에이전트 파이프라인 실행 중..."):
                    output = run_phase1_analysis(query, user_profile=user_profile, portfolio=portfolio)
                st.session_state["analysis_output"] = output
                if output.state.user_request:
                    st.session_state["intake_messages"].append(
                        {
                            "role": "assistant",
                            "content": (
                                f"질문 유형은 {output.state.user_request.intent}, "
                                f"긴급도는 {output.state.user_request.urgency_reason}로 분류했어요."
                            ),
                        }
                    )
                st.rerun()
        with col_edit:
            if st.button("포트폴리오 다시 입력"):
                st.session_state.pop("analysis_output", None)
                st.session_state.pop("analysis_target", None)
                st.session_state.pop("analysis_query", None)
                st.session_state.pop("analysis_query_target", None)
                st.rerun()

        _render_output()

    return portfolio


def _render_portfolio_summary(portfolio: Portfolio) -> None:
    st.write("포트폴리오 요약")
    total_value = portfolio.total_market_value or 0
    col_total, col_cash = st.columns(2)
    col_total.metric("총 평가금액", f"{total_value:,}원")
    col_cash.metric("현금 비중", f"{portfolio.cash_weight:.0%}")

    for holding in portfolio.holdings:
        weight_label = f"{holding.weight:.0%}" if holding.weight is not None else "계산 불가"
        market_value = holding.market_value or 0
        cost_basis = holding.cost_basis or 0
        pnl_rate = (
            (market_value - cost_basis) / cost_basis
            if cost_basis > 0 and market_value > 0
            else 0
        )
        st.write(
            f"- {holding.corp_name}: {holding.qty}주 / 평단 {(holding.avg_price or 0):,}원 / "
            f"평가 {market_value:,}원 / 손익률 {pnl_rate:.1%} / {weight_label}"
        )

    sector_weights = portfolio.sector_weights()
    if sector_weights:
        st.write("섹터 비중")
        for sector, weight in sector_weights.items():
            st.progress(weight, text=f"{sector} {weight:.0%}")


def _build_initial_query(portfolio: Portfolio) -> str:
    if portfolio.holdings:
        names = ", ".join(holding.corp_name for holding in portfolio.holdings[:3])
        return f"{names} 보유 포트폴리오를 투자성향 기준으로 먼저 점검해줘"
    return "현재 포트폴리오를 투자성향 기준으로 먼저 점검해줘"


def _analysis_target_options(portfolio: Portfolio) -> list[str]:
    options = ["전체 보유 종목"]
    options.extend(holding.corp_name for holding in portfolio.holdings)
    return options


def _default_analysis_query(target: str, portfolio: Portfolio) -> str:
    if target == "전체 보유 종목":
        holding_names = ", ".join(holding.corp_name for holding in portfolio.holdings[:3])
        if holding_names:
            return f"내 보유 종목 전체({holding_names})를 분석해줘"
        return "내 보유 종목 전체를 분석해줘"
    return f"{target} 급등했는데 어떻게 할까?"



def _render_output() -> None:
    output = st.session_state.get("analysis_output")
    if output is None:
        st.info("질문을 실행하면 분류 결과와 분석 결과가 표시됩니다.")
        return

    tier1 = output.tier1
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
    st.markdown(
        """
        <style>
        .stApp {
            background: #f8fafc;
            color: #0f172a;
        }
        div[data-testid="stMetric"],
        div[data-testid="stStatus"] {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 0.75rem;
        }
        div[data-testid="stNumberInput"] label p,
        div[data-testid="stMultiSelect"] label p {
            font-size: 0.85rem;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("단계형 투자성향 수집")
    st.caption("질문 카드에 하나씩 답하면 투자성향을 추론하고, 보유 종목을 받아 분석합니다.")

    stage = st.session_state["intake_stage"]
    if stage == "onboarding":
        _render_onboarding_step()
    else:
        user_profile = _get_inferred_profile()
        _render_portfolio_step(user_profile)


if __name__ == "__main__":
    main()
