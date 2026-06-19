from html import escape
from typing import Any

import streamlit as st

from stock_agent.graph import stream_phase1_analysis_events
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


_AGENT_PROGRESS_ORDER = [
    "curator",
    "classifier",
    "quant",
    "qual",
    "competitor",
    "macro",
    "strategist",
    "investment_analyst",
    "guardrail",
]

_AGENT_LABELS = {
    "curator": "Curator",
    "classifier": "RequestClassifier",
    "quant": "Quant",
    "qual": "Qual",
    "competitor": "Competitor",
    "macro": "Macro",
    "strategist": "Strategist",
    "investment_analyst": "InvestmentAnalyst",
    "guardrail": "Guardrail",
}

_STATUS_LABELS = {
    "pending": "대기",
    "done": "완료",
    "skipped": "스킵",
    "error": "오류",
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
    st.session_state.setdefault("intake_portfolio", None)
    st.session_state.setdefault("intake_messages", [])


def _reset_intake() -> None:
    for key in [
        "intake_stage",
        "onboarding_step",
        "onboarding_answers",
        "inferred_profile",
        "cash_amount",
        "intake_portfolio",
        "analysis_output",
        "agent_events",
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

    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("성향 질문으로 돌아가기"):
            st.session_state["intake_stage"] = "onboarding"
            st.rerun()
    with col_next:
        if st.button("투자성향 확인", type="primary", disabled=not portfolio.holdings):
            st.session_state["intake_portfolio"] = portfolio.model_dump(mode="json")
            st.session_state.pop("analysis_output", None)
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


def _clean_progress_text(value: Any, limit: int = 110) -> str:
    text = str(value or "").replace("\n", " ").replace("|", "/").strip()
    if len(text) > limit:
        return text[: limit - 1] + "..."
    return text


def _initial_agent_progress() -> dict[str, dict[str, str]]:
    return {
        name: {
            "label": _AGENT_LABELS[name],
            "status": "pending",
            "detail": "",
        }
        for name in _AGENT_PROGRESS_ORDER
    }


def _render_agent_progress(
    placeholder: Any,
    progress: dict[str, dict[str, str]],
    *,
    title: str = "에이전트 실행 로그",
) -> None:
    active = next(
        (item["label"] for item in progress.values() if item["status"] == "pending"),
        "완료",
    )
    cards = []
    for item in progress.values():
        status = item["status"]
        cards.append(
            "<div class='agent-card agent-card-{status}'>"
            "<div class='agent-card-top'>"
            "<span class='agent-name'>{label}</span>"
            "<span class='agent-status'>{status_label}</span>"
            "</div>"
            "<div class='agent-detail'>{detail}</div>"
            "</div>".format(
                status=escape(status),
                label=escape(_clean_progress_text(item["label"], 36)),
                status_label=escape(_STATUS_LABELS.get(status, status)),
                detail=escape(_clean_progress_text(item.get("detail"), 86)) or "&nbsp;",
            )
        )

    html = """
    <div class="agent-progress-panel">
      <div class="agent-progress-head">
        <div>
          <div class="agent-progress-title">{title}</div>
          <div class="agent-progress-sub">현재 작업: {active}</div>
        </div>
        <div class="robot-worker" aria-label="agent worker">
          <div class="robot-antenna"></div>
          <div class="robot-head">
            <span class="robot-eye"></span>
            <span class="robot-eye"></span>
          </div>
          <div class="robot-body">
            <span class="robot-panel"></span>
          </div>
          <div class="robot-arm robot-arm-left"></div>
          <div class="robot-arm robot-arm-right"></div>
          <div class="robot-shadow"></div>
        </div>
      </div>
      <div class="agent-card-grid">{cards}</div>
    </div>
    """.format(
        title=escape(title),
        active=escape(_clean_progress_text(active, 60)),
        cards="".join(cards),
    )
    placeholder.markdown(html, unsafe_allow_html=True)


def _progress_from_events(events: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    progress = _initial_agent_progress()
    for event in events:
        node = event.get("node")
        if node not in progress:
            continue
        progress[node] = {
            "label": event.get("label") or _AGENT_LABELS[node],
            "status": event.get("status") or "done",
            "detail": event.get("detail") or "",
        }
    return progress


def _run_analysis_with_progress(
    query: str,
    *,
    user_profile: UserProfile,
    portfolio: Portfolio,
) -> Any:
    progress = _initial_agent_progress()
    events: list[dict[str, Any]] = []
    output = None
    with st.status("LangGraph 에이전트 실행 중", expanded=True) as status:
        progress_placeholder = st.empty()
        _render_agent_progress(progress_placeholder, progress)
        for event in stream_phase1_analysis_events(
            query,
            user_profile=user_profile,
            portfolio=portfolio,
        ):
            if event["type"] == "complete":
                output = event["output"]
                continue
            node = event["node"]
            if node in progress:
                progress[node] = {
                    "label": event["label"],
                    "status": event["status"],
                    "detail": event["detail"],
                }
                events.append(
                    {
                        "node": node,
                        "label": event["label"],
                        "status": event["status"],
                        "detail": event["detail"],
                    }
                )
                _render_agent_progress(progress_placeholder, progress)
                status.update(label=f"{event['label']} 완료", state="running", expanded=True)
        if output is None:
            status.update(label="LangGraph 실패", state="error", expanded=True)
            raise RuntimeError("analysis pipeline did not produce output")
        status.update(label="LangGraph 에이전트 실행 완료", state="complete", expanded=False)
    st.session_state["agent_events"] = events
    return output


def _ensure_initial_analysis_output(user_profile: UserProfile, portfolio: Portfolio) -> None:
    if st.session_state.get("analysis_output") is not None:
        return
    output = _run_analysis_with_progress(
        _build_initial_query(portfolio),
        user_profile=user_profile,
        portfolio=portfolio,
    )
    st.session_state["analysis_output"] = output


def _render_analysis_step(user_profile: UserProfile, portfolio: Portfolio) -> None:
    _render_profile_summary(user_profile)
    st.success(
        f"답변을 바탕으로 현재 투자성향은 {_format_risk_label(user_profile.risk_tolerance)}으로 추론했습니다."
    )
    st.subheader("3. 저장된 포트폴리오")
    _render_portfolio_summary(portfolio)

    _render_output()

    st.subheader("4. 대화형 질문")
    if st.session_state["intake_messages"]:
        for message in st.session_state["intake_messages"]:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    query = st.text_input(
        "궁금한 점을 입력해 주세요",
        value="삼성전자 급등했는데 안정형이면 어떻게 할까?",
        placeholder="예: SK하이닉스 비중 괜찮아?",
    )

    col_run, col_edit = st.columns([1, 1])
    with col_run:
        if st.button("분석 실행", type="primary"):
            st.session_state["intake_messages"].append({"role": "user", "content": query})
            output = _run_analysis_with_progress(
                query,
                user_profile=user_profile,
                portfolio=portfolio,
            )
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
            st.session_state["intake_stage"] = "portfolio"
            st.session_state.pop("analysis_output", None)
            st.rerun()


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

    if output.state.strategist:
        st.write("Graph 상태")
        route = output.state.graph_route
        col_route, col_agents, col_model = st.columns(3)
        col_route.metric("graph route", route.get("analysis_scope") or "unknown")
        col_agents.metric(
            "contributing agents",
            ", ".join(output.state.strategist.contributing_agents) or "none",
        )
        col_model.metric(
            "model",
            f"{output.state.strategist.model_provider}/{output.state.strategist.model}",
        )
        st.caption(
            f"degraded={output.state.strategist.degraded} | "
            f"fallback_used={output.state.strategist.fallback_used} | "
            f"requested_depth={route.get('requested_depth')}"
        )
        if output.state.worker_errors:
            st.warning(" / ".join(output.state.worker_errors))

    events = st.session_state.get("agent_events") or []
    if events:
        progress_placeholder = st.empty()
        _render_agent_progress(
            progress_placeholder,
            _progress_from_events(events),
            title="마지막 에이전트 실행 로그",
        )

    tabs = st.tabs(["정량", "정성", "Peer", "거시", "적합도", "리스크"])
    for tab, key in zip(
        tabs,
        ["정량 근거", "정성 근거", "Peer 비교", "거시경제", "포트폴리오 적합도", "리스크"],
        strict=True,
    ):
        with tab:
            for item in output.tier2.get(key, []):
                if key == "거시경제":
                    # [논문출처] 태그 제거 후 본문만 표시, 데이터 출처는 고정 caption으로
                    bracket_idx = item.rfind("[")
                    main_text = item[:bracket_idx].strip() if "[" in item else item
                    st.write(f"- {main_text}")
                    st.caption("  📎 데이터 출처: 한국은행 ECOS API")
                else:
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
        section.main > div.block-container {
            max-width: 1500px;
            padding-left: 2rem;
            padding-right: 2rem;
        }
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
        .agent-progress-panel {
            width: 100%;
            margin: 0.25rem 0 0.5rem;
            border: 1px solid #dbe4ef;
            border-radius: 8px;
            background: #ffffff;
            padding: 0.9rem;
        }
        .agent-progress-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 0.75rem;
        }
        .agent-progress-title {
            font-size: 0.98rem;
            font-weight: 800;
            color: #0f172a;
        }
        .agent-progress-sub {
            margin-top: 0.15rem;
            font-size: 0.82rem;
            color: #64748b;
        }
        .agent-card-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
            gap: 0.55rem;
            width: 100%;
        }
        .agent-card {
            min-height: 84px;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            background: #f8fafc;
            padding: 0.65rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        .agent-card-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.45rem;
            margin-bottom: 0.45rem;
        }
        .agent-name {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 0.82rem;
            font-weight: 800;
            color: #0f172a;
        }
        .agent-status {
            flex: 0 0 auto;
            border-radius: 999px;
            padding: 0.13rem 0.45rem;
            font-size: 0.7rem;
            font-weight: 800;
            background: #e2e8f0;
            color: #475569;
        }
        .agent-detail {
            color: #64748b;
            font-size: 0.74rem;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }
        .agent-card-done {
            border-color: #99f6e4;
            background: #f0fdfa;
        }
        .agent-card-done .agent-status {
            background: #0f766e;
            color: #ffffff;
        }
        .agent-card-skipped {
            border-color: #fed7aa;
            background: #fff7ed;
        }
        .agent-card-skipped .agent-status {
            background: #c2410c;
            color: #ffffff;
        }
        .agent-card-error {
            border-color: #fecaca;
            background: #fef2f2;
        }
        .agent-card-error .agent-status {
            background: #b91c1c;
            color: #ffffff;
        }
        .robot-worker {
            position: relative;
            width: 58px;
            height: 70px;
            flex: 0 0 58px;
            animation: robot-float 1.6s ease-in-out infinite;
        }
        .robot-antenna {
            position: absolute;
            left: 27px;
            top: 0;
            width: 3px;
            height: 11px;
            background: #475569;
            border-radius: 999px;
        }
        .robot-antenna::after {
            content: "";
            position: absolute;
            left: -4px;
            top: -5px;
            width: 11px;
            height: 11px;
            border-radius: 50%;
            background: #22c55e;
            box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.12);
        }
        .robot-head {
            position: absolute;
            left: 10px;
            top: 12px;
            width: 38px;
            height: 28px;
            border: 2px solid #334155;
            border-radius: 8px;
            background: #e0f2fe;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .robot-eye {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #0f172a;
            animation: robot-blink 2.4s ease-in-out infinite;
        }
        .robot-body {
            position: absolute;
            left: 15px;
            top: 42px;
            width: 28px;
            height: 20px;
            border: 2px solid #334155;
            border-radius: 6px;
            background: #ffffff;
        }
        .robot-panel {
            position: absolute;
            left: 8px;
            top: 6px;
            width: 12px;
            height: 5px;
            border-radius: 999px;
            background: #14b8a6;
            animation: robot-panel 1s ease-in-out infinite;
        }
        .robot-arm {
            position: absolute;
            top: 45px;
            width: 14px;
            height: 4px;
            border-radius: 999px;
            background: #334155;
            transform-origin: center;
        }
        .robot-arm-left {
            left: 4px;
            animation: robot-arm-left 0.9s ease-in-out infinite;
        }
        .robot-arm-right {
            right: 4px;
            animation: robot-arm-right 0.9s ease-in-out infinite;
        }
        .robot-shadow {
            position: absolute;
            left: 11px;
            bottom: 0;
            width: 36px;
            height: 6px;
            border-radius: 999px;
            background: rgba(15, 23, 42, 0.13);
            animation: robot-shadow 1.6s ease-in-out infinite;
        }
        @keyframes robot-float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-4px); }
        }
        @keyframes robot-blink {
            0%, 92%, 100% { transform: scaleY(1); }
            95% { transform: scaleY(0.15); }
        }
        @keyframes robot-panel {
            0%, 100% { opacity: 0.45; }
            50% { opacity: 1; }
        }
        @keyframes robot-arm-left {
            0%, 100% { transform: rotate(-18deg); }
            50% { transform: rotate(18deg); }
        }
        @keyframes robot-arm-right {
            0%, 100% { transform: rotate(18deg); }
            50% { transform: rotate(-18deg); }
        }
        @keyframes robot-shadow {
            0%, 100% { transform: scaleX(1); opacity: 0.13; }
            50% { transform: scaleX(0.8); opacity: 0.08; }
        }
        @media (max-width: 760px) {
            section.main > div.block-container {
                padding-left: 0.9rem;
                padding-right: 0.9rem;
            }
            .agent-card-grid {
                grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
            }
            .agent-progress-head {
                align-items: flex-start;
            }
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


if __name__ == "__main__":
    main()