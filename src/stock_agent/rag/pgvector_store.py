from __future__ import annotations

from typing import Any

from stock_agent.config import get_settings
from stock_agent.db import get_connection


def _format_vector(values: list[float]) -> str:
    settings = get_settings()
    if len(values) != settings.embedding_dimensions:
        raise ValueError(
            f"embedding dimension mismatch: expected {settings.embedding_dimensions}, got {len(values)}"
        )
    return "[" + ",".join(str(float(value)) for value in values) + "]"


def search_similar_chunks(
    query_embedding: list[float],
    *,
    stock_code: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    vector = _format_vector(query_embedding)
    stock_filter = "AND d.stock_code = %(stock_code)s" if stock_code else ""

    sql = f"""
        SELECT
            c.id,
            c.document_id,
            d.source_type,
            d.source,
            d.title,
            d.url,
            d.published_at,
            d.stock_code,
            c.chunk_index,
            c.content,
            1 - (c.embedding <=> %(embedding)s::vector) AS score
        FROM rag_chunks c
        JOIN rag_documents d ON d.id = c.document_id
        WHERE c.embedding IS NOT NULL
        {stock_filter}
        ORDER BY c.embedding <=> %(embedding)s::vector
        LIMIT %(limit)s
    """

    params = {"embedding": vector, "stock_code": stock_code, "limit": limit}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [desc.name for desc in cur.description]
            return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]
