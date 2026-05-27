import streamlit as st

from stock_agent.graph import build_demo_profile, run_phase1_analysis
from stock_agent.schemas import Holding, Portfolio, UserProfile


_SECTOR_OPTIONS = ["반도체", "금융"]
_STOCK_OPTIONS = {
    "삼성전자": {"stock_code": "005930", "sector": "반도체", "current_price": 78000},
    "SK하이닉스": {"stock_code": "000660", "sector": "반도체", "current_price": 201000},
    "KB금융": {"stock_code": "105560", "sector": "금융", "current_price": 82000},
    "신한지주": {"stock_code": "055550", "sector": "금융", "current_price": 56000},
}


def _signal_badge(signal: str) -> str:
    colors = {"BUY": "#0f766e", "HOLD": "#b45309", "SELL": "#b91c1c"}
    return (
        f"<span style='background:{colors.get(signal, '#334155')}; color:white; "
        "padding:0.25rem 0.55rem; border-radius:0.35rem; font-weight:700;'>"
        f"{signal}</span>"
    )


def _build_holding_weights(holdings: list[Holding]) -> list[Holding]:
    total_value = sum(holding.market_value or 0 for holding in holdings)
    if total_value <= 0:
        return holdings
    return [
        holding.model_copy(update={"weight": (holding.market_value or 0) / total_value})
        for holding in holdings
    ]


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
        target_return_rate = st.slider("목표 수익률", min_value=0, max_value=50, value=10) / 100
        max_drawdown_tolerance = -st.slider("허용 손실률", min_value=0, max_value=50, value=10) / 100
        investment_goal = st.selectbox(
            "투자 목적",
            options=["growth", "wealth_preservation", "short_term_profit", "dividend"],
            format_func={
                "wealth_preservation": "안정적 자산관리",
                "growth": "중장기 성장",
                "short_term_profit": "단기 수익",
                "dividend": "배당",
            }.get,
        )
        experience_level = st.selectbox(
            "투자 경험",
            options=["beginner", "intermediate", "advanced"],
            format_func={"beginner": "초보", "intermediate": "중급", "advanced": "고급"}.get,
        )
        preferred_sectors = st.multiselect(
            "관심 산업",
            options=_SECTOR_OPTIONS,
            default=["반도체"],
        )
        cash_weight = st.slider("현금 비중", min_value=0, max_value=100, value=20) / 100

        st.caption("회원가입/DB 저장 전까지는 입력값을 세션 안에서만 사용합니다.")
        st.write("보유 종목")
        holding_count = st.number_input("종목 수", min_value=1, max_value=5, value=2, step=1)
        draft_holdings: list[Holding] = []
        for index in range(holding_count):
            default_holding = demo_portfolio.holdings[min(index, len(demo_portfolio.holdings) - 1)]
            with st.expander(f"종목 {index + 1}", expanded=index == 0):
                corp_name = st.selectbox(
                    "종목",
                    options=list(_STOCK_OPTIONS),
                    index=list(_STOCK_OPTIONS).index(default_holding.corp_name)
                    if default_holding.corp_name in _STOCK_OPTIONS
                    else 0,
                    key=f"holding_corp_name_{index}",
                )
                stock = _STOCK_OPTIONS[corp_name]
                avg_price = st.number_input(
                    "평균 매수가",
                    min_value=1,
                    value=default_holding.avg_price or stock["current_price"],
                    step=100,
                    key=f"holding_avg_price_{index}",
                )
                qty = st.number_input(
                    "수량",
                    min_value=1,
                    value=default_holding.qty or 1,
                    step=1,
                    key=f"holding_qty_{index}",
                )
                draft_holdings.append(
                    Holding(
                        stock_code=str(stock["stock_code"]),
                        corp_name=corp_name,
                        sector=str(stock["sector"]),
                        avg_price=int(avg_price),
                        qty=int(qty),
                        current_price=int(stock["current_price"]),
                    )
                )

        holdings = _build_holding_weights(draft_holdings)
        for holding in holdings:
            weight_label = f"{holding.weight:.0%}" if holding.weight is not None else "계산 불가"
            st.write(f"- {holding.corp_name} {weight_label}")

        validation_errors: list[str] = []
        if not preferred_sectors:
            validation_errors.append("관심 산업을 1개 이상 선택해 주세요.")
        if not holdings:
            validation_errors.append("보유 종목을 1개 이상 입력해 주세요.")
        stock_codes = [holding.stock_code for holding in holdings]
        if len(stock_codes) != len(set(stock_codes)):
            validation_errors.append("같은 종목이 중복 입력되어 있습니다.")

    user_profile = UserProfile(
        user_id=demo_profile.user_id,
        risk_tolerance=risk_label,
        investment_horizon_months=horizon,
        target_return_rate=target_return_rate,
        max_drawdown_tolerance=max_drawdown_tolerance,
        investment_goal=investment_goal,
        experience_level=experience_level,
        cash_source=demo_profile.cash_source,
        preferred_sectors=preferred_sectors,
    )
    portfolio = Portfolio(holdings=holdings, cash_weight=cash_weight)

    st.title("국내 주식 포트폴리오 분석")
    st.caption("Curator -> Quant/Qual/Competitor -> Strategist -> Guardrail")

    query = st.text_input(
        "질문",
        value="내 포트폴리오에서 삼성전자 어떻게 할까?",
        placeholder="예: 내 포트폴리오에서 삼성전자 어떻게 할까?",
    )

    if validation_errors:
        for error in validation_errors:
            st.error(error)

    if st.button("분석 실행", type="primary", use_container_width=False, disabled=bool(validation_errors)):
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
