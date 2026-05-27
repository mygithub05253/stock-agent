from stock_agent.schemas.analysis import AgentState, StrategistResult


def _detect_price_event(query: str) -> str | None:
    if any(keyword in query for keyword in ("급등", "상승", "올랐")):
        return "surge"
    if any(keyword in query for keyword in ("급락", "하락", "떨어졌")):
        return "drop"
    return None


def run_strategist(state: AgentState) -> AgentState:
    if state.quant is None or state.qual is None or state.competitor is None:
        raise ValueError("quant, qual, and competitor results are required before strategy")

    aggregate_score = round((state.quant.score * 0.45) + (state.qual.score * 0.3) + (state.competitor.score * 0.25))
    signal = "BUY" if aggregate_score >= 76 else "SELL" if aggregate_score <= 44 else "HOLD"

    holding_weight = 0.0
    if state.curator is not None:
        holding_weight = sum(
            holding.weight or 0
            for holding in state.portfolio.holdings
            if holding.stock_code == state.curator.stock_code
        )
    suitability = aggregate_score - round(holding_weight * 20)
    if state.user_profile.risk_tolerance == "low":
        suitability -= 8 if holding_weight >= 0.3 else 3
    elif state.user_profile.risk_tolerance == "high":
        suitability += 5

    if state.user_profile.liquidity_need_level == "high":
        suitability -= 5
    if state.user_profile.max_drawdown_tolerance is not None and state.user_profile.max_drawdown_tolerance > -0.08:
        suitability -= 4
    if state.user_profile.investment_horizon_months < 6:
        suitability -= 3

    suitability = max(30, min(90, suitability))
    raw_query = state.user_request.raw_query if state.user_request else state.user_query
    price_event = (
        state.user_request.urgency_reason
        if state.user_request and state.user_request.urgency_reason in {"surge", "drop"}
        else _detect_price_event(raw_query)
    )

    next_actions = [
        "보유 비중이 이미 높다면 추가 매수보다 실적 발표와 업황 지표 확인을 우선합니다.",
        "신규 진입은 단일 가격보다 분할 매수 기준가와 손실 허용 범위를 먼저 정합니다.",
    ]
    if state.user_profile.risk_tolerance == "low" and holding_weight >= 0.3:
        next_actions.insert(0, "안정형 성향 대비 보유 비중이 높아 비중 확대보다 리밸런싱 기준을 먼저 정합니다.")
    if price_event == "surge":
        next_actions.append("급등 이후에는 추격 매수보다 목표 비중과 이익 실현 기준을 먼저 확인합니다.")
    elif price_event == "drop":
        next_actions.append("급락 이후에는 손실 허용 범위와 추가 하락 시 대응 기준을 먼저 확인합니다.")

    state.strategist = StrategistResult(
        signal=signal,
        confidence=aggregate_score,
        suitability=suitability,
        headline="종목 분석 신호와 사용자 포트폴리오 적합도를 분리해 보면 보유 유지 검토가 우세합니다.",
        key_reasons=[
            state.quant.reasons[0],
            state.qual.evidence[0],
            state.competitor.peer_summary,
        ],
        risks=[
            state.quant.risks[0],
            state.qual.risks[0],
            "투자성향, 보유 비중, 현금 필요도가 맞지 않으면 종목 신호가 양호해도 포트폴리오 적합도는 낮아질 수 있습니다.",
        ],
        next_actions=next_actions,
    )
    return state
