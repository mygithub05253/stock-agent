from stock_agent.schemas.analysis import AgentState, QualResult


def classify_event_types(texts: list[str]) -> list[str]:
    """
    뉴스/공시 근거 문장들을 기반으로 정성 이벤트 유형을 분류합니다.
    현재는 mock RAG 단계이므로 keyword rule 기반으로 구현합니다.
    이후 LLM 분류기 또는 RAG 결과 기반 분류기로 교체할 수 있습니다.
    """
    joined_text = " ".join(texts)

    event_types = []

    if any(keyword in joined_text for keyword in ["실적", "매출", "영업이익", "순이익", "이익률"]):
        event_types.append("실적")

    if any(keyword in joined_text for keyword in ["AI", "반도체", "수요", "업황", "산업", "사이클"]):
        event_types.append("산업 트렌드")

    if any(keyword in joined_text for keyword in ["신사업", "투자", "인수", "합병", "M&A", "고대역폭", "선단 공정"]):
        event_types.append("신사업")

    if any(keyword in joined_text for keyword in ["규제", "소송", "제재", "리스크", "불확실성"]):
        event_types.append("규제/리스크")

    if any(keyword in joined_text for keyword in ["환율", "금리", "물가", "경기", "거시"]):
        event_types.append("매크로")

    return event_types or ["기타"]


def classify_sentiment(evidence: list[str], risks: list[str]) -> str:
    """
    긍정 근거와 리스크 개수를 바탕으로 간단한 sentiment를 산출합니다.
    추후 뉴스 sentiment score 또는 LLM 판단 결과로 교체 가능합니다.
    """
    if len(evidence) > len(risks):
        return "positive"
    if len(evidence) < len(risks):
        return "negative"
    return "neutral"


def calculate_qual_score(sentiment: str, evidence: list[str], risks: list[str]) -> int:
    """
    정성 분석 점수를 0~100 범위로 계산합니다.
    현재는 단순 rule 기반 mock scoring입니다.
    """
    base_score = 50

    if sentiment == "positive":
        base_score += 15
    elif sentiment == "negative":
        base_score -= 15

    base_score += min(len(evidence) * 3, 15)
    base_score -= min(len(risks) * 4, 20)

    return max(0, min(100, base_score))


def run_qual(state: AgentState) -> AgentState:
    if state.curator is None:
        raise ValueError("curator result is required before qualitative analysis")

    evidence = [
        "AI 서버 수요 확대가 고대역폭 메모리와 선단 공정 투자 기대를 높이고 있습니다.",
        "최근 공시와 보도에서는 반도체 사이클 회복이 핵심 논점으로 반복됩니다.",
        "모바일과 가전 수요는 회복 강도가 아직 제한적이라는 점이 함께 언급됩니다.",
    ]

    risks = [
        "뉴스/공시 RAG가 아직 mock이므로 실제 출처 기반 검증이 필요합니다.",
        "업황 뉴스가 기대 중심일 경우 실적 확인 전까지 신뢰도를 보수적으로 봐야 합니다.",
    ]

    event_types = classify_event_types(evidence + risks)
    sentiment = classify_sentiment(evidence, risks)
    score = calculate_qual_score(sentiment, evidence, risks)

    state.qual = QualResult(
        score=score,
        sentiment=sentiment,
        event_types=event_types,
        evidence=evidence,
        risks=risks,
    )

    return state