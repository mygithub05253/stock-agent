from html import escape
from io import BytesIO
from datetime import datetime
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import streamlit as st

from stock_agent.graph import stream_phase1_analysis_events
from stock_agent.intake import (
    STOCK_CATALOG,
    build_holding_from_selection,
    build_portfolio_from_holdings,
    get_stock_options,
    get_onboarding_card,
    infer_user_profile,
    onboarding_card_count,
)
from stock_agent.schemas import Portfolio, UserProfile


_DEFAULT_AVG_PRICE_RATIO_BY_CORP = {
    "SK하이닉스": 0.92,
    "삼성전자": 0.95,
    "한미반도체": 0.9,
    "KB금융": 0.94,
    "신한지주": 0.96,
}

_DEFAULT_QTY_BY_CORP = {
    "SK하이닉스": 1,
    "삼성전자": 2,
    "한미반도체": 1,
    "리노공업": 1,
    "이오테크닉스": 1,
    "DB하이텍": 2,
    "HPSP": 2,
    "ISC": 1,
    "이수페타시스": 2,
    "하나마이크론": 2,
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


def _clear_analysis_state() -> None:
    for key in ["analysis_output", "agent_events", "intake_messages"]:
        st.session_state.pop(key, None)
    st.session_state.setdefault("intake_messages", [])


def _clear_portfolio_state() -> None:
    for key in ["intake_portfolio", "cash_amount"]:
        st.session_state.pop(key, None)
    _clear_analysis_state()
    st.session_state.setdefault("cash_amount", 0)


def _clear_profile_state() -> None:
    st.session_state.pop("inferred_profile", None)
    _clear_portfolio_state()


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
            if answers.get(card["id"]) != selected_option["value"]:
                _clear_profile_state()
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

    cash_amount = st.number_input(
        "보유 현금",
        min_value=0,
        value=st.session_state["cash_amount"],
        step=100000,
        format="%d",
    )
    st.session_state["cash_amount"] = int(cash_amount)
    portfolio = build_portfolio_from_holdings(selected_holdings, int(cash_amount))
    if portfolio.holdings:
        _render_portfolio_summary(portfolio)
    else:
        st.info("보유 종목을 1개 이상 선택해 주세요.")

    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("성향 질문으로 돌아가기"):
            _clear_profile_state()
            st.session_state["intake_stage"] = "onboarding"
            st.rerun()
    with col_next:
        if st.button("투자성향 확인", type="primary", disabled=not portfolio.holdings):
            st.session_state["intake_portfolio"] = portfolio.model_dump(mode="json")
            _clear_analysis_state()
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
            _clear_analysis_state()
            st.session_state["intake_stage"] = "portfolio"
            st.rerun()


def _artifact_basename(output: Any) -> str:
    stock_code = getattr(output.state.curator, "stock_code", None) if output.state.curator else None
    date_part = datetime.now().strftime("%Y%m%d")
    return f"stock_agent_{stock_code or 'report'}_{date_part}"


def _section_rows(output: Any) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = [
        ("signal", output.tier1.signal),
        ("confidence", f"{output.tier1.confidence}%"),
        ("suitability", f"{output.tier1.suitability}%"),
        ("headline", output.tier1.headline),
        ("disclaimer", output.tier1.disclaimer),
    ]
    if output.state.curator:
        rows.extend(
            [
                ("corp_name", output.state.curator.corp_name),
                ("stock_code", output.state.curator.stock_code),
                ("corp_code", output.state.curator.corp_code),
                ("sector", output.state.curator.sector),
            ]
        )
    return rows


def _build_html_report(output: Any) -> bytes:
    rr = output.state.rendered_report
    sections = []
    for title, items in output.tier2.items():
        section_items = "".join(f"<li>{escape(str(item))}</li>" for item in items)
        sections.append(f"<section><h2>{escape(title)}</h2><ul>{section_items}</ul></section>")
    tier3_items = "".join(
        f"<li><strong>{escape(name)}</strong>: {escape(value)}</li>"
        for name, value in output.tier3.items()
    )
    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>stock-agent report</title>
  <style>
    body {{ font-family: Arial, "Noto Sans KR", sans-serif; margin: 32px; color: #0f172a; }}
    header {{ border-bottom: 2px solid #0f766e; padding-bottom: 16px; margin-bottom: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    h2 {{ margin-top: 24px; color: #0f766e; font-size: 18px; }}
    .badge {{ display: inline-block; padding: 4px 10px; border-radius: 999px; background: #0f766e; color: white; font-weight: 700; }}
    .metric {{ display: inline-block; margin-right: 12px; padding: 8px 10px; border: 1px solid #dbe4ef; border-radius: 8px; }}
    section {{ margin-bottom: 18px; }}
    li {{ margin: 7px 0; line-height: 1.55; }}
    .notice {{ color: #475569; font-size: 13px; }}
  </style>
</head>
<body>
  <header>
    <h1>{escape(output.tier1.headline)}</h1>
    <p><span class="badge">{escape(output.tier1.signal)}</span></p>
    <p>
      <span class="metric">신뢰도 {output.tier1.confidence}%</span>
      <span class="metric">포트폴리오 적합도 {output.tier1.suitability}%</span>
    </p>
    <p class="notice">{escape(output.tier1.disclaimer)}</p>
  </header>
  {f"<section><h2>요약</h2><p>{escape(rr.summary)}</p><p>{escape(rr.recommendation)}</p></section>" if rr else ""}
  {''.join(sections)}
  <section><h2>Tier 3 산출물 상태</h2><ul>{tier3_items}</ul></section>
</body>
</html>
"""
    return html.encode("utf-8")


def _xml_text(value: Any) -> str:
    return escape(str(value), quote=True)


def _xlsx_col_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _xlsx_sheet(rows: list[list[Any]]) -> str:
    row_xml = []
    for r_idx, row in enumerate(rows, start=1):
        cells = []
        for c_idx, value in enumerate(row, start=1):
            ref = f"{_xlsx_col_name(c_idx)}{r_idx}"
            cells.append(
                f'<c r="{ref}" t="inlineStr"><is><t>{_xml_text(value)}</t></is></c>'
            )
        row_xml.append(f'<row r="{r_idx}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData></worksheet>'
    )


def _build_excel_report(output: Any) -> bytes:
    summary_rows = [["항목", "값"], *[list(row) for row in _section_rows(output)]]
    tier2_rows = [["섹션", "내용"]]
    for section, items in output.tier2.items():
        tier2_rows.extend([[section, item] for item in items])
    tier3_rows = [["산출물", "상태"], *[[name, value] for name, value in output.tier3.items()]]
    quant_rows = [["지표", "값"]]
    if output.state.quant:
        quant_rows.extend([[name, value] for name, value in output.state.quant.metrics.items()])
    sheets = [
        ("Summary", summary_rows),
        ("Tier2", tier2_rows),
        ("Tier3", tier3_rows),
        ("Quant", quant_rows),
    ]

    workbook_sheets = "".join(
        f'<sheet name="{name}" sheetId="{idx}" r:id="rId{idx}"/>'
        for idx, (name, _rows) in enumerate(sheets, start=1)
    )
    workbook_rels = "".join(
        f'<Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{idx}.xml"/>'
        for idx in range(1, len(sheets) + 1)
    )
    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for idx in range(1, len(sheets) + 1)
    )

    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            f"{overrides}</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        zf.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<sheets>{workbook_sheets}</sheets></workbook>",
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f"{workbook_rels}</Relationships>",
        )
        for idx, (_name, rows) in enumerate(sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{idx}.xml", _xlsx_sheet(rows))
    return buffer.getvalue()


def _pdf_text(text: str) -> str:
    return "<" + text.encode("utf-16-be").hex().upper() + ">"


def _build_pdf_report(output: Any) -> bytes:
    lines = [
        "stock-agent PB 리포트",
        output.tier1.headline,
        f"판단: {output.tier1.signal} / 신뢰도: {output.tier1.confidence}% / 적합도: {output.tier1.suitability}%",
        output.tier1.disclaimer,
        "",
        "[투자 근거]",
        *[f"- {item}" for item in (output.state.rendered_report.strengths if output.state.rendered_report else [])[:6]],
        "",
        "[리스크]",
        *[f"- {item}" for item in (output.state.rendered_report.risks if output.state.rendered_report else [])[:6]],
        "",
        "[권장 행동]",
        *[f"- {item}" for item in (output.state.rendered_report.actions if output.state.rendered_report else [])[:4]],
    ]
    content_lines = ["BT", "/F1 13 Tf", "50 790 Td"]
    for idx, line in enumerate(lines[:34]):
        if idx:
            content_lines.append("0 -21 Td")
        content_lines.append(f"{_pdf_text(line[:58])} Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type0 /BaseFont /HYGoThic-Medium /Encoding /UniKS-UCS2-H /DescendantFonts [6 0 R] >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /HYGoThic-Medium /CIDSystemInfo << /Registry (Adobe) /Ordering (Korea1) /Supplement 2 >> >>",
    ]
    pdf = BytesIO()
    pdf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(pdf.tell())
        pdf.write(f"{idx} 0 obj\n".encode("ascii"))
        pdf.write(obj)
        pdf.write(b"\nendobj\n")
    xref_at = pdf.tell()
    pdf.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.write(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return pdf.getvalue()


def _render_download_artifacts(output: Any) -> None:
    basename = _artifact_basename(output)
    st.markdown("#### 산출물 다운로드")
    col_pdf, col_xlsx, col_html = st.columns(3)
    with col_pdf:
        st.download_button(
            "PDF 리포트",
            data=_build_pdf_report(output),
            file_name=f"{basename}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with col_xlsx:
        st.download_button(
            "Excel 밸류에이션",
            data=_build_excel_report(output),
            file_name=f"{basename}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with col_html:
        st.download_button(
            "HTML 분석",
            data=_build_html_report(output),
            file_name=f"{basename}.html",
            mime="text/html",
            use_container_width=True,
        )


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

    # Rendered report (Tier cards)
    if output.state.rendered_report:
        rr = output.state.rendered_report
        tier3_items = "".join(
            f"<li><span class='tier-card-muted'>{escape(name)}</span><br>"
            f"{escape(value)}</li>"
            for name, value in output.tier3.items()
        )
        strength_items = "".join(f"<li>{escape(item)}</li>" for item in rr.strengths[:4])
        risk_items = "".join(f"<li>{escape(item)}</li>" for item in rr.risks[:4])
        action_items = "".join(f"<li>{escape(item)}</li>" for item in rr.actions[:4])

        st.subheader("요약 카드")
        st.markdown(
            f"""
            <div class="tier-grid">
              <section class="tier-card tier-card-primary">
                <div class="tier-card-kicker">Tier 1 · 핵심 판단</div>
                <h3>{escape(rr.summary)}</h3>
                <div class="tier-card-metrics">
                  <span>판단 <b>{escape(rr.recommendation)}</b></span>
                  <span>신뢰도 <b>{tier1.confidence}%</b></span>
                  <span>적합도 <b>{tier1.suitability}%</b></span>
                </div>
              </section>
              <section class="tier-card">
                <div class="tier-card-kicker">Tier 2 · 투자 근거</div>
                <ul class="tier-list tier-list-good">{strength_items or "<li>표시할 근거가 없습니다.</li>"}</ul>
              </section>
              <section class="tier-card">
                <div class="tier-card-kicker">Tier 3 · 리스크</div>
                <ul class="tier-list tier-list-warn">{risk_items or "<li>표시할 리스크가 없습니다.</li>"}</ul>
              </section>
              <section class="tier-card">
                <div class="tier-card-kicker">다음 행동</div>
                <ul class="tier-list">{action_items or "<li>추가 행동 제안이 없습니다.</li>"}</ul>
              </section>
              <section class="tier-card tier-card-disabled">
                <div class="tier-card-kicker">Tier 3 · 산출물</div>
                <ul class="tier-list">{tier3_items}</ul>
                <div class="tier-card-note">아래 버튼으로 현재 분석 결과를 파일로 내려받을 수 있습니다.</div>
              </section>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _render_download_artifacts(output)

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
        .tier-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
            gap: 0.75rem;
            margin: 0.5rem 0 1rem;
        }
        .tier-card {
            border: 1px solid #dbe4ef;
            border-radius: 8px;
            background: #ffffff;
            padding: 0.95rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
        }
        .tier-card-primary {
            grid-column: 1 / -1;
            border-color: #99f6e4;
            background: linear-gradient(180deg, #f0fdfa 0%, #ffffff 100%);
        }
        .tier-card-disabled {
            background: #f8fafc;
            border-style: dashed;
        }
        .tier-card-kicker {
            margin-bottom: 0.45rem;
            color: #0f766e;
            font-size: 0.78rem;
            font-weight: 900;
            letter-spacing: 0.02em;
        }
        .tier-card h3 {
            margin: 0.1rem 0 0.65rem;
            color: #0f172a;
            font-size: 1.2rem;
            line-height: 1.35;
        }
        .tier-card-metrics {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
        }
        .tier-card-metrics span {
            border: 1px solid #ccfbf1;
            border-radius: 999px;
            background: #ffffff;
            padding: 0.28rem 0.65rem;
            color: #334155;
            font-size: 0.82rem;
        }
        .tier-list {
            margin: 0;
            padding-left: 1.15rem;
            color: #334155;
        }
        .tier-list li {
            margin: 0.42rem 0;
            line-height: 1.45;
        }
        .tier-list-good li::marker {
            color: #0f766e;
        }
        .tier-list-warn li::marker {
            color: #b45309;
        }
        .tier-card-muted {
            color: #64748b;
            font-weight: 800;
        }
        .tier-card-note {
            margin-top: 0.65rem;
            border-radius: 8px;
            background: #e2e8f0;
            padding: 0.45rem 0.6rem;
            color: #475569;
            font-size: 0.8rem;
            font-weight: 700;
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
            .tier-grid {
                grid-template-columns: 1fr;
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
