from stock_agent.rag.retriever import retrieve_disclosures, retrieve_news
from stock_agent.schemas.analysis import AgentState, QualResult


def classify_event_types(texts: list[str]) -> list[str]:
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
    if len(evidence) > len(risks):
        return "positive"
    if len(evidence) < len(risks):
        return "negative"
    return "neutral"


def calculate_qual_score(sentiment: str, evidence: list[str], risks: list[str]) -> int:
    base_score = 50

    if sentiment == "positive":
        base_score += 15
    elif sentiment == "negative":
        base_score -= 15

    base_score += min(len(evidence) * 3, 15)
    base_score -= min(len(risks) * 4, 20)

    return max(0, min(100, base_score))


def is_risk_text(text: str) -> bool:
    risk_keywords = [
        "리스크",
        "불확실",
        "감소",
        "둔화",
        "제한적",
        "악화",
        "부진",
        "하락",
        "규제",
        "소송",
        "적자",
    ]

    return any(keyword in text for keyword in risk_keywords)


def format_doc_as_evidence(doc: dict) -> str:
    title = doc.get("title") or doc.get("report_nm") or "제목 없음"
    body = doc.get("body", "")
    source = doc.get("publisher") or doc.get("source_url") or ""

    if source:
        return f"{title}: {body} (출처: {source})"

    return f"{title}: {body}"


def run_qual(state: AgentState) -> AgentState:
    if state.curator is None:
        raise ValueError("curator result is required before qualitative analysis")

    ticker = getattr(state.curator, "ticker", None) or getattr(state.curator, "stock_code", None)
    corp_code = getattr(state.curator, "corp_code", "")

    news_docs = retrieve_news(
        ticker=ticker,
        query="최근 호재 악재 실적 산업 트렌드 신사업 리스크",
        k=5,
    )

    disclosure_docs = retrieve_disclosures(
        corp_code=corp_code,
        query="최근 공시 사업보고서 리스크 신사업 실적",
        k=3,
    )

    all_docs = news_docs + disclosure_docs

    evidence = [
        format_doc_as_evidence(doc)
        for doc in all_docs
        if doc.get("body")
    ]

    risks = [
        format_doc_as_evidence(doc)
        for doc in all_docs
        if doc.get("body") and is_risk_text(doc["body"])
    ]

    if not risks:
        risks = ["검색된 뉴스에서 명확한 부정 리스크는 발견되지 않았으나, 업황 변동성과 실적 확인 전 불확실성은 고려해야 합니다."]

    if not evidence:
        evidence = ["뉴스 임베딩 검색 결과가 없어 정성 분석 근거가 부족합니다."]

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