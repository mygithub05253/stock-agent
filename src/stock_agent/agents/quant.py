from stock_agent.schemas.analysis import AgentState, QuantResult


def run_quant(state: AgentState) -> AgentState:
    if state.curator is None:
        raise ValueError("curator result is required before quant analysis")

    state.quant = QuantResult(
        score=72,
        valuation_signal="HOLD",
        metrics={
            "per": 18.4,
            "pbr": 1.35,
            "roe": 7.8,
            "revenue_growth_yoy": 16.2,
            "debt_ratio": 26.4,
            "volatility_60d": 24.1,
            "momentum_20d": 3.6,
        },
        reasons=[
            "최근 매출 성장률과 20일 모멘텀이 개선되어 단기 회복 신호가 있습니다.",
            "부채비율은 낮은 편이라 재무 안정성 리스크는 제한적입니다.",
            "PER은 이익 회복 기대를 일부 반영해 저평가로 단정하기 어렵습니다.",
        ],
        risks=[
            "메모리 업황 회복 속도가 둔화되면 이익 추정치가 낮아질 수 있습니다.",
            "단기 변동성이 높아 추가 매수 시 분할 접근이 필요합니다.",
        ],
    )
    return state
