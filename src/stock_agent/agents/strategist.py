from stock_agent.schemas.analysis import AgentState, StrategistResult


def run_strategist(state: AgentState) -> AgentState:
    if state.quant is None or state.qual is None or state.competitor is None:
        raise ValueError("quant, qual, and competitor results are required before strategy")

    aggregate_score = round((state.quant.score * 0.45) + (state.qual.score * 0.3) + (state.competitor.score * 0.25))
    signal = "BUY" if aggregate_score >= 76 else "SELL" if aggregate_score <= 44 else "HOLD"

    holding_weight = 0.0
    if state.curator is not None:
        holding_weight = sum(
            holding.weight
            for holding in state.portfolio.holdings
            if holding.stock_code == state.curator.stock_code
        )
    suitability = max(45, min(85, aggregate_score - round(holding_weight * 20)))

    state.strategist = StrategistResult(
        signal=signal,
        confidence=aggregate_score,
        suitability=suitability,
        headline="현재 데이터 기준으로는 보유 유지 성격의 분석 신호가 우세합니다.",
        key_reasons=[
            state.quant.reasons[0],
            state.qual.evidence[0],
            state.competitor.peer_summary,
        ],
        risks=[
            state.quant.risks[0],
            state.qual.risks[0],
        ],
        next_actions=[
            "보유 비중이 이미 높다면 추가 매수보다 실적 발표와 업황 지표 확인을 우선합니다.",
            "신규 진입은 단일 가격보다 분할 매수 기준가와 손실 허용 범위를 먼저 정합니다.",
        ],
    )
    return state
