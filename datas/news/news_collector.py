import os
import re
import time
import json
import hashlib
import requests
import psycopg2
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin
from dotenv import load_dotenv

# 뉴스 데이터 수집 파이프라인
# company 테이블에 저장된 종목을 기준으로 네이버 금융 뉴스를 수집합니다.
# MVP 기준: 최근 6개월 뉴스만 수집하고, raw_news / rag_documents 테이블에 적재합니다.

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

NAVER_FINANCE_NEWS_URL = "https://finance.naver.com/item/news_news.naver"
NAVER_BASE_URL = "https://finance.naver.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.naver.com/",
}


def clean_text(text):
    """뉴스 제목/요약의 불필요한 공백을 정리합니다."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_naver_datetime(raw_text):
    """
    네이버 금융 뉴스 날짜 문자열을 datetime으로 변환합니다.
    예: 2026.05.23 14:30
    """
    raw_text = clean_text(raw_text)

    if not raw_text:
        return None

    for fmt in ("%Y.%m.%d %H:%M", "%Y.%m.%d"):
        try:
            return datetime.strptime(raw_text, fmt)
        except ValueError:
            continue

    return None


def make_external_id(source, url, title):
    """같은 뉴스가 중복 저장되지 않도록 source + url + title 기반 해시를 생성합니다."""
    raw = f"{source}|{url}|{title}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def classify_event_type(title, summary=""):
    """
    MVP용 룰 기반 이벤트 분류입니다.
    추후 KoFinBERT/LLM 기반 분류로 교체 가능합니다.
    """
    text = f"{title} {summary}"

    rules = [
        ("earnings", ["실적", "매출", "영업이익", "순이익", "흑자", "적자", "어닝"]),
        ("regulation", ["규제", "금감원", "공정위", "제재", "소송", "벌금"]),
        ("contract", ["수주", "계약", "공급", "납품", "MOU"]),
        ("mna", ["인수", "합병", "매각", "지분", "투자 유치"]),
        ("industry_trend", ["AI", "반도체", "HBM", "배터리", "전기차", "바이오", "클라우드"]),
        ("macro", ["금리", "환율", "CPI", "물가", "유가", "나스닥", "코스피"]),
        ("risk", ["하락", "급락", "우려", "리스크", "부진", "차질", "약세"]),
    ]

    for event_type, keywords in rules:
        for keyword in keywords:
            if keyword.lower() in text.lower():
                return event_type

    return "general"


def calculate_sentiment_score(title, summary=""):
    """
    MVP용 단순 감성 점수입니다.
    - positive 키워드가 많으면 양수
    - negative 키워드가 많으면 음수
    """
    text = f"{title} {summary}"

    positive_words = [
        "상승", "강세", "호재", "개선", "증가", "성장", "수주", "흑자",
        "기대", "회복", "최대", "돌파", "상향", "매수"
    ]

    negative_words = [
        "하락", "약세", "악재", "부진", "감소", "적자", "우려", "리스크",
        "차질", "소송", "규제", "하향", "매도", "급락"
    ]

    pos_count = sum(1 for word in positive_words if word in text)
    neg_count = sum(1 for word in negative_words if word in text)

    if pos_count == 0 and neg_count == 0:
        return 0.0

    score = (pos_count - neg_count) / max(pos_count + neg_count, 1)
    return round(max(min(score, 1.0), -1.0), 2)


def get_target_companies(cursor, limit=9):
    """
    company 테이블에서 뉴스 수집 대상 기업을 가져옵니다.
    MVP 시연 안정성을 위해 기본 9개 종목만 대상으로 합니다.
    """
    cursor.execute("""
        SELECT corp_code, stock_code, corp_name, sector
        FROM company
        WHERE stock_code IS NOT NULL
        ORDER BY corp_name
        LIMIT %s;
    """, (limit,))

    return cursor.fetchall()


def fetch_naver_finance_news(stock_code, corp_code, corp_name, page_count=3, months=6):
    """
    네이버 금융 종목 뉴스 목록을 수집합니다.
    최근 months개월 안의 뉴스만 반환합니다.
    """
    print(f"  -> 네이버 금융 뉴스 수집 시작: {corp_name}({stock_code})")

    cutoff_date = datetime.today() - timedelta(days=months * 30)
    collected_news = []

    for page in range(1, page_count + 1):
        params = {
            "code": stock_code,
            "page": page,
            "sm": "title_entity_id.basic",
            "clusterId": "",
        }

        try:
            response = requests.get(
                NAVER_FINANCE_NEWS_URL,
                params=params,
                headers=HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            response.encoding = "euc-kr"
        except Exception as e:
            print(f"  -> 네이버 뉴스 요청 실패 page={page}: {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("table.type5 tr")

        for row in rows:
            title_tag = row.select_one("td.title a")
            date_tag = row.select_one("td.date")

            if not title_tag:
                continue

            title = clean_text(title_tag.get_text(" ", strip=True))
            href = title_tag.get("href")
            url = urljoin(NAVER_BASE_URL, href) if href else None

            if not title or not url:
                continue

            published_at = parse_naver_datetime(date_tag.get_text(" ", strip=True) if date_tag else "")

            if published_at and published_at < cutoff_date:
                continue

            summary = ""
            next_row = row.find_next_sibling("tr")
            if next_row:
                summary_tag = next_row.select_one("td")
                if summary_tag:
                    summary = clean_text(summary_tag.get_text(" ", strip=True))

            source = "naver_finance"
            external_id = make_external_id(source, url, title)
            event_type = classify_event_type(title, summary)
            sentiment_score = calculate_sentiment_score(title, summary)

            collected_news.append({
                "source": source,
                "external_id": external_id,
                "corp_code": corp_code,
                "stock_code": stock_code,
                "company_name": corp_name,
                "title": title,
                "summary": summary,
                "url": url,
                "published_at": published_at,
                "event_type": event_type,
                "sentiment_score": sentiment_score,
            })

        time.sleep(0.5)

    deduplicated = {}
    for item in collected_news:
        deduplicated[item["external_id"]] = item

    return list(deduplicated.values())


def insert_raw_news(cursor, news):
    """raw_news 테이블에 원천 뉴스 payload를 저장합니다."""
    payload = {
        "corp_code": news["corp_code"],
        "stock_code": news["stock_code"],
        "company_name": news["company_name"],
        "source": news["source"],
        "title": news["title"],
        "summary": news["summary"],
        "url": news["url"],
        "published_at": news["published_at"].isoformat() if news["published_at"] else None,
        "event_type": news["event_type"],
        "sentiment_score": news["sentiment_score"],
    }

    query = """
        INSERT INTO raw_news (source, external_id, title, published_at, payload)
        VALUES (%s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (source, external_id)
        DO UPDATE SET
            title = EXCLUDED.title,
            published_at = EXCLUDED.published_at,
            payload = EXCLUDED.payload,
            collected_at = NOW();
    """

    cursor.execute(
        query,
        (
            news["source"],
            news["external_id"],
            news["title"],
            news["published_at"],
            json.dumps(payload, ensure_ascii=False),
        )
    )


def insert_rag_document(cursor, news):
    """
    rag_documents 테이블에 RAG 검색용 문서를 저장합니다.
    현재는 제목 + 요약을 content로 사용합니다.
    추후 기사 본문 전문 수집 후 content를 확장할 수 있습니다.
    """
    content = clean_text(f"{news['title']}\n\n{news['summary']}")

    if not content:
        return

    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    metadata = {
        "company_name": news["company_name"],
        "event_type": news["event_type"],
        "sentiment_score": news["sentiment_score"],
        "collector": "datas/news/collector.py",
    }

    query = """
        INSERT INTO rag_documents (
            source_type,
            source,
            external_id,
            corp_code,
            stock_code,
            title,
            url,
            published_at,
            content,
            content_hash,
            metadata
        )
        VALUES (
            'news',
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s::jsonb
        )
        ON CONFLICT (source_type, source, external_id)
        WHERE external_id IS NOT NULL
        DO UPDATE SET
            title = EXCLUDED.title,
            url = EXCLUDED.url,
            published_at = EXCLUDED.published_at,
            content = EXCLUDED.content,
            content_hash = EXCLUDED.content_hash,
            metadata = EXCLUDED.metadata,
            updated_at = NOW();
    """

    cursor.execute(
        query,
        (
            news["source"],
            news["external_id"],
            news["corp_code"],
            news["stock_code"],
            news["title"],
            news["url"],
            news["published_at"],
            content,
            content_hash,
            json.dumps(metadata, ensure_ascii=False),
        )
    )


def collect_news():
    """
    뉴스 수집 전체 파이프라인 실행 함수입니다.
    DART collector.py와 동일하게 단일 실행 진입점으로 사용합니다.
    """
    print("뉴스 데이터 수집 파이프라인 시작...")

    if not DATABASE_URL:
        print("DATABASE_URL 누락")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return

    try:
        companies = get_target_companies(cursor, limit=9)

        if not companies:
            print("수집 대상 기업이 없습니다. company 테이블을 먼저 확인하세요.")
            return

        print(f"뉴스 수집 대상 기업 수: {len(companies)}개")

        total_count = 0

        for idx, (corp_code, stock_code, corp_name, sector) in enumerate(companies, 1):
            print(f"\n[{idx}/{len(companies)}] {corp_name}({stock_code}) 뉴스 수집 중...")

            try:
                news_list = fetch_naver_finance_news(
                    stock_code=stock_code,
                    corp_code=corp_code,
                    corp_name=corp_name,
                    page_count=3,
                    months=6,
                )

                print(f"  -> 수집 후보 뉴스: {len(news_list)}건")

                inserted_count = 0

                for news in news_list:
                    insert_raw_news(cursor, news)
                    insert_rag_document(cursor, news)
                    inserted_count += 1

                conn.commit()
                total_count += inserted_count

                print(f"  -> DB 적재 완료: {inserted_count}건")

            except Exception as e:
                conn.rollback()
                print(f"  -> {corp_name} 뉴스 수집 실패 패스: {e}")

            time.sleep(1.0)

        print(f"\n최종 완료: 뉴스 데이터 총 {total_count}건 적재/갱신 완료")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    collect_news()