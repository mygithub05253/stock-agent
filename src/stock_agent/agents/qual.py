from stock_agent.schemas.analysis import AgentState, QualResult


def run_qual(state: AgentState) -> AgentState:
    if state.curator is None:
        raise ValueError("curator result is required before qualitative analysis")

    state.qual = QualResult(
        score=68,
        sentiment="positive",
        event_types=["실적", "산업 트렌드", "신사업"],
        evidence=[
            "AI 서버 수요 확대가 고대역폭 메모리와 선단 공정 투자 기대를 높이고 있습니다.",
            "최근 공시와 보도에서는 반도체 사이클 회복이 핵심 논점으로 반복됩니다.",
            "모바일과 가전 수요는 회복 강도가 아직 제한적이라는 점이 함께 언급됩니다.",
        ],
        risks=[
            "뉴스/공시 RAG가 아직 mock이므로 실제 출처 기반 검증이 필요합니다.",
            "업황 뉴스가 기대 중심일 경우 실적 확인 전까지 신뢰도를 보수적으로 봐야 합니다.",
        ],
    )
    return state
