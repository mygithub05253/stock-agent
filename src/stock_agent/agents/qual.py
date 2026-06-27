from stock_agent.agents.fallback import ensure_database_available, fallback_reason, should_fallback
from stock_agent.schemas.analysis import AgentState, QualResult


_SAMSUNG_FALLBACK_NEWS_DOCS = [
    {
        "title": "메모리 업종 변동성 확대",
        "body": (
            "메모리 가격 상승이 소비자 제품 가격 부담으로 이어질 수 있다는 우려가 커지며 "
            "삼성전자와 SK하이닉스 등 메모리 관련주의 단기 변동성이 확대됐습니다. AI 서버 "
            "수요와 일반 소비재 수요의 온도 차이를 함께 봐야 합니다."
        ),
        "publisher": "Barron's, 2026-06-26",
        "source_url": "https://www.barrons.com/articles/micron-stock-price-sk-hynix-samsung-kospi-459506f7",
        "stock_code": "005930",
    },
    {
        "title": "SK하이닉스 HBM 선점에 따른 경쟁 압력",
        "body": (
            "HBM 시장에서 SK하이닉스가 AI 수요를 선점하며 삼성전자의 상대 경쟁력이 투자자 "
            "관심사로 부각됐습니다. 삼성전자는 HBM4 공급과 고부가 제품 확대 속도가 핵심 "
            "리스크입니다."
        ),
        "publisher": "Reuters/Investing.com, 2026-06-24",
        "source_url": (
            "https://www.investing.com/news/stock-market-news/"
            "how-sk-hynixs-bet-on-a-niche-memory-chip-made-it-more-valuable-than-samsung-4757282"
        ),
        "stock_code": "005930",
    },
    {
        "title": "HBM4와 NVIDIA 협력 논의",
        "body": (
            "삼성전자 반도체 부문 경영진은 NVIDIA와 HBM4 및 파운드리 협력 방안을 논의했다고 "
            "밝혔습니다. AI 가속기 생태계에서 고부가 메모리와 첨단 공정 수요를 확보할 수 있는 "
            "호재입니다."
        ),
        "publisher": "Reuters Connect, 2026-06-08",
        "source_url": (
            "https://www.reutersconnect.com/item/"
            "samsung-elecs-chip-chief-says-he-discussed-next-generation-foundry-with-nvidia-ceo/"
            "dGFnOnJldXRlcnMuY29tLDIwMjY6bmV3c21sX1ZBNjkyMzA4MDYyMDI2UlAx"
        ),
        "stock_code": "005930",
    },
    {
        "title": "삼성전자 Q1 2026 실적 발표",
        "body": (
            "삼성전자는 2026년 1분기 연결 매출 133.9조원, 영업이익 57.2조원을 발표했습니다. "
            "메모리 사업은 AI 수요와 평균판매가격 상승에 힘입어 분기 최대 수준의 실적을 냈습니다."
        ),
        "publisher": "Samsung Newsroom, 2026-06-05",
        "source_url": "https://news.samsung.com/ca/samsung-electronics-announces-first-quarter-2026-results",
        "stock_code": "005930",
    },
]


def _with_fallback_reason(docs: list[dict], reason: str) -> list[dict]:
    return [{**doc, "fallback_reason": reason} for doc in docs]


def fallback_news_docs(ticker: str | None, reason: str) -> list[dict]:
    stock_code = ticker or ""
    if stock_code == "005930":
        return _with_fallback_reason(_SAMSUNG_FALLBACK_NEWS_DOCS, reason)

    return [
        {
            "title": "최근 산업 수요 점검",
            "body": (
                "AI, 반도체, 전장 등 주요 수요처의 투자 흐름을 기준으로 업황 개선 가능성을 "
                "점검해야 합니다."
            ),
            "publisher": "임시 뉴스 데이터",
            "stock_code": stock_code,
            "fallback_reason": reason,
        },
        {
            "title": "실적 모멘텀 확인 필요",
            "body": (
                "매출 성장률, 영업이익률, 재고 조정 속도가 투자 판단의 핵심 변수입니다. "
                "실적 발표 전까지는 보수적인 가정이 필요합니다."
            ),
            "publisher": "임시 뉴스 데이터",
            "stock_code": stock_code,
            "fallback_reason": reason,
        },
        {
            "title": "업황 변동성 리스크",
            "body": (
                "환율, 금리, 고객사 주문 변동에 따라 단기 실적과 밸류에이션이 흔들릴 수 "
                "있어 리스크 관리가 필요합니다."
            ),
            "publisher": "임시 뉴스 데이터",
            "stock_code": stock_code,
            "fallback_reason": reason,
        }
    ]


def fallback_disclosure_docs(corp_code: str | None, reason: str) -> list[dict]:
    company_code = corp_code or ""
    return [
        {
            "report_nm": "최근 공시 주요 체크포인트",
            "body": (
                "사업보고서와 분기보고서에서 매출 구성, 수익성, 투자 계획, 우발채무 변화를 "
                "확인해야 합니다."
            ),
            "source_url": "임시 공시 데이터",
            "corp_code": company_code,
            "fallback_reason": reason,
        },
        {
            "report_nm": "공시 리스크 점검",
            "body": (
                "신규 투자, 재고, 소송, 차입 부담, 고객사 집중도는 정성 리스크로 별도 "
                "점검이 필요합니다."
            ),
            "source_url": "임시 공시 데이터",
            "corp_code": company_code,
            "fallback_reason": reason,
        }
    ]


def retrieve_news_with_fallback(ticker: str | None) -> list[dict]:
    try:
        ensure_database_available()
        from stock_agent.rag.retriever import retrieve_news

        return retrieve_news(
            ticker=ticker,
            query="최근 호재 악재 실적 산업 트렌드 신사업 리스크",
            k=5,
        )
    except Exception as exc:
        if not should_fallback(exc):
            raise
        return fallback_news_docs(ticker, fallback_reason(exc))


def retrieve_disclosures_with_fallback(corp_code: str | None) -> list[dict]:
    try:
        ensure_database_available()
        from stock_agent.rag.retriever import retrieve_disclosures

        return retrieve_disclosures(
            corp_code=corp_code,
            query="최근 공시 사업보고서 리스크 신사업 실적",
            k=3,
        )
    except Exception as exc:
        if not should_fallback(exc):
            raise
        return fallback_disclosure_docs(corp_code, fallback_reason(exc))


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
    source_url = doc.get("source_url")
    retrieval_method = doc.get("retrieval_method")
    rrf_score = doc.get("rrf_score")
    similarity = doc.get("similarity")
    keyword_score = doc.get("keyword_score")

    if source:
        evidence = f"{title}: {body} (출처: {source})"
    else:
        evidence = f"{title}: {body}"

    retrieval_parts = []
    if retrieval_method:
        retrieval_parts.append(f"method={retrieval_method}")
    if rrf_score is not None:
        retrieval_parts.append(f"rrf_score={rrf_score:.4f}")
    if similarity is not None:
        retrieval_parts.append(f"similarity={similarity:.4f}")
    if keyword_score is not None:
        retrieval_parts.append(f"keyword_score={keyword_score:.4f}")
    if source_url and source_url != source:
        retrieval_parts.append(f"url={source_url}")
    if retrieval_parts:
        evidence = f"{evidence} [{' | '.join(retrieval_parts)}]"

    return evidence


def run_qual(state: AgentState) -> AgentState:
    if state.curator is None:
        raise ValueError("curator result is required before qualitative analysis")

    ticker = getattr(state.curator, "ticker", None) or getattr(state.curator, "stock_code", None)
    corp_code = getattr(state.curator, "corp_code", "")

    news_docs = retrieve_news_with_fallback(ticker)
    disclosure_docs = retrieve_disclosures_with_fallback(corp_code)

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
