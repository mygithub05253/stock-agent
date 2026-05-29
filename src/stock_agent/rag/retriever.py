from typing import Any

from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from stock_agent.db import get_connection


EMBEDDING_MODEL = "BAAI/bge-m3"


def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL)


def retrieve_news(ticker: str, query: str, k: int = 5) -> list[dict[str, Any]]:
    model = get_embedding_model()
    query_embedding = model.encode(query).tolist()

    with get_connection() as conn:
        register_vector(conn)

        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    id,
                    stock_code,
                    title,
                    body,
                    source_url,
                    publisher,
                    published_at,
                    event_type,
                    sentiment,
                    1 - (embedding <=> %s) as similarity
                from news_chunks
                where (%s is null or stock_code = %s)
                  and embedding is not null
                order by embedding <=> %s
                limit %s
                """,
                (
                    query_embedding,
                    ticker,
                    ticker,
                    query_embedding,
                    k,
                ),
            )

            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


def retrieve_disclosures(corp_code: str, query: str, k: int = 5) -> list[dict[str, Any]]:
    return []from typing import Any

from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from stock_agent.db import get_connection


EMBEDDING_MODEL = "BAAI/bge-m3"


def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL)


def retrieve_news(ticker: str, query: str, k: int = 5) -> list[dict[str, Any]]:
    model = get_embedding_model()
    query_embedding = model.encode(query).tolist()

    with get_connection() as conn:
        register_vector(conn)

        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    id,
                    stock_code,
                    title,
                    body,
                    source_url,
                    publisher,
                    published_at,
                    event_type,
                    sentiment,
                    1 - (embedding <=> %s) as similarity
                from news_chunks
                where (%s is null or stock_code = %s)
                  and embedding is not null
                order by embedding <=> %s
                limit %s
                """,
                (
                    query_embedding,
                    ticker,
                    ticker,
                    query_embedding,
                    k,
                ),
            )

            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


def retrieve_disclosures(corp_code: str, query: str, k: int = 5) -> list[dict[str, Any]]:
    return []