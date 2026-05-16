from stock_agent.schemas.analysis import AgentState, CompetitorResult


def run_competitor(state: AgentState) -> AgentState:
    if state.curator is None:
        raise ValueError("curator result is required before competitor analysis")

    state.competitor = CompetitorResult(
        score=64,
        peer_summary="국내 반도체 대형주 대비 밸류에이션은 중립, 재무 안정성은 우위입니다.",
        peers=[
            {"corp_name": "삼성전자", "per": 18.4, "pbr": 1.35, "roe": 7.8},
            {"corp_name": "SK하이닉스", "per": 22.7, "pbr": 1.92, "roe": 8.5},
            {"corp_name": "DB하이텍", "per": 11.8, "pbr": 0.88, "roe": 6.4},
        ],
        evidence=[
            "Peer 대비 PBR 부담은 중간 수준입니다.",
            "ROE는 업황 회복 전 구간이라 아직 강한 우위로 보기 어렵습니다.",
            "현금 여력과 사업 포트폴리오 분산은 방어 요인입니다.",
        ],
    )
    return state
