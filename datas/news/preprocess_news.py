import os
import re
import json
import hashlib
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

# 뉴스 전처리 파이프라인
# raw_news에 저장된 원천 뉴스 payload를 읽어서 정제한 뒤
# rag_documents 테이블에 RAG 검색용 문서로 저장/갱신합니다.

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def clean_text(text):
    """뉴스 제목/요약/본문의 불필요한 공백과 제어문자를 정리합니다."""
    if not text:
        return ""

    text = re.sub(r"<[^>]+>", " ", text)          # HTML 태그 제거
    text = re.sub(r"\s+", " ", text)             # 연속 공백 제거
    text = text.replace("\u200b", "")            # zero-width space 제거
    text = text.strip()

    return text


def normalize_datetime(value):
    """
    published_at 값을 DB에 넣기 좋은 datetime 또는 None으로 정리합니다.
    raw_news payload에는 문자열로 들어갈 수 있으므로 방어적으로 처리합니다.
    """
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(value[:19], fmt)
            except ValueError:
                continue

    return None


def classify_event_type(title, summary=""):
    """
    MVP용 룰 기반 이벤트 분류.
    collector.py와 같은 기준을 유지합니다.
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
    """MVP용 단순 감성 점수 계산."""
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


def make_content_hash(content):
    """정제된 content 기준으로 중복 판단용 hash 생성."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def fetch_raw_news(cursor, limit=1000):
    """
    raw_news 테이블에서 전처리 대상 뉴스를 가져옵니다.
    최신 수집 순서로 제한하여 처리합니다.
    """
    cursor.execute("""
        SELECT source, external_id, title, published_at, payload
        FROM raw_news
        ORDER BY collected_at DESC
        LIMIT %s;
    """, (limit,))

    return cursor.fetchall()


def build_rag_document(raw_row):
    """
    raw_news 한 건을 rag_documents 저장용 dict로 변환합니다.
    """
    source, external_id, title, published_at, payload = raw_row

    if isinstance(payload, str):
        payload = json.loads(payload)

    payload = payload or {}

    stock_code = payload.get("stock_code")
    corp_code = payload.get("corp_code")
    company_name = payload.get("company_name")
    url = payload.get("url")
    summary = payload.get("summary") or ""

    clean_title = clean_text(title or payload.get("title"))
    clean_summary = clean_text(summary)

    if not clean_title and not clean_summary:
        return None

    event_type = payload.get("event_type") or classify_event_type(clean_title, clean_summary)
    sentiment_score = payload.get("sentiment_score")
    if sentiment_score is None:
        sentiment_score = calculate_sentiment_score(clean_title, clean_summary)

    content = clean_text(f"{clean_title}\n\n{clean_summary}")
    content_hash = make_content_hash(content)

    normalized_published_at = published_at or normalize_datetime(payload.get("published_at"))

    metadata = {
        "company_name": company_name,
        "event_type": event_type,
        "sentiment_score": sentiment_score,
        "preprocessor": "datas/news/preprocess_news.py",
    }

    return {
        "source_type": "news",
        "source": source,
        "external_id": external_id,
        "corp_code": corp_code,
        "stock_code": stock_code,
        "title": clean_title,
        "url": url,
        "published_at": normalized_published_at,
        "content": content,
        "content_hash": content_hash,
        "metadata": metadata,
    }


def upsert_rag_document(cursor, doc):
    """정제된 뉴스 문서를 rag_documents에 저장/갱신합니다."""
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
            %s, %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, %s, %s::jsonb
        )
        ON CONFLICT (source_type, source, external_id)
        WHERE external_id IS NOT NULL
        DO UPDATE SET
            corp_code = EXCLUDED.corp_code,
            stock_code = EXCLUDED.stock_code,
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
            doc["source_type"],
            doc["source"],
            doc["external_id"],
            doc["corp_code"],
            doc["stock_code"],
            doc["title"],
            doc["url"],
            doc["published_at"],
            doc["content"],
            doc["content_hash"],
            json.dumps(doc["metadata"], ensure_ascii=False),
        )
    )


def preprocess_news():
    """
    뉴스 전처리 전체 실행 함수.
    raw_news → rag_documents 흐름을 안정화합니다.
    """
    print("뉴스 전처리 파이프라인 시작...")

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
        raw_news_rows = fetch_raw_news(cursor, limit=1000)

        if not raw_news_rows:
            print("전처리할 raw_news 데이터가 없습니다.")
            return

        print(f"전처리 대상 뉴스: {len(raw_news_rows)}건")

        success_count = 0
        skipped_count = 0

        for idx, raw_row in enumerate(raw_news_rows, 1):
            try:
                doc = build_rag_document(raw_row)

                if not doc:
                    skipped_count += 1
                    continue

                upsert_rag_document(cursor, doc)
                success_count += 1

                if idx % 50 == 0:
                    conn.commit()
                    print(f"  -> {idx}/{len(raw_news_rows)}건 처리 중...")

            except Exception as e:
                skipped_count += 1
                print(f"  -> 전처리 실패 패스 idx={idx}: {e}")

        conn.commit()

        print(f"전처리 완료: 성공 {success_count}건 / 패스 {skipped_count}건")

    except Exception as e:
        conn.rollback()
        print(f"치명적 오류 발생: {e}")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    preprocess_news()
