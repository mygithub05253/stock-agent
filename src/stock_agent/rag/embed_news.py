from typing import Any

from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from stock_agent.db import get_connection


EMBEDDING_MODEL = "BAAI/bge-m3"


def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL)


def get_text_from_raw_news(news: dict[str, Any]) -> str:
    return (
        news.get("body")
        or news.get("content")
        or news.get("summary")
        or news.get("title")
        or ""
    )


def fetch_raw_news(limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select *
                from raw_news
                limit %s
                """,
                (limit,),
            )

            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


def insert_news_chunk(news: dict[str, Any], embedding: list[float]) -> None:
    text = get_text_from_raw_news(news)

    with get_connection() as conn:
        register_vector(conn)

        with conn.cursor() as cur:
            cur.execute(
                """
                insert into news_chunks (
                    stock_code,
                    title,
                    body,
                    source_url,
                    publisher,
                    published_at,
                    event_type,
                    sentiment,
                    embedding
                )
                values (
                    %(stock_code)s,
                    %(title)s,
                    %(body)s,
                    %(source_url)s,
                    %(publisher)s,
                    %(published_at)s,
                    %(event_type)s,
                    %(sentiment)s,
                    %(embedding)s
                )
                """,
                {
                    "stock_code": news.get("stock_code"),
                    "title": news.get("title"),
                    "body": text,
                    "source_url": news.get("url") or news.get("source_url"),
                    "publisher": news.get("publisher") or news.get("source"),
                    "published_at": news.get("published_at"),
                    "event_type": news.get("event_type"),
                    "sentiment": news.get("sentiment"),
                    "embedding": embedding,
                },
            )

        conn.commit()


def embed_raw_news(limit: int = 50) -> None:
    model = get_embedding_model()
    raw_news = fetch_raw_news(limit=limit)

    if not raw_news:
        print("raw_news에 뉴스 데이터가 없습니다.")
        return

    for idx, news in enumerate(raw_news, start=1):
        text = get_text_from_raw_news(news)

        if not text:
            print(f"[{idx}] 본문/제목이 없어 skip")
            continue

        embedding = model.encode(text).tolist()
        insert_news_chunk(news, embedding)

        print(f"[{idx}/{len(raw_news)}] embedded: {news.get('title')}")


if __name__ == "__main__":
    embed_raw_news(limit=50)