from typing import Any

from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from stock_agent.db import get_connection


EMBEDDING_MODEL = "BAAI/bge-m3"
RRF_K = 60


def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL)


def _rows_to_dicts(columns: list[str], rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    return [dict(zip(columns, row)) for row in rows]


def _hybrid_search(
    *,
    source_type: str,
    query: str,
    stock_code: str | None = None,
    corp_code: str | None = None,
    k: int = 5,
) -> list[dict[str, Any]]:
    candidate_limit = max(k * 4, 20)

    try:
        with get_connection() as conn:
            register_vector(conn)
            model = get_embedding_model()
            encoded_query = model.encode(query)
            query_embedding = (
                encoded_query.tolist() if hasattr(encoded_query, "tolist") else encoded_query
            )

            with conn.cursor() as cur:
                cur.execute(
                    """
                    with filtered_chunks as (
                        select
                            c.id,
                            c.content,
                            c.embedding,
                            c.search_tsv,
                            d.source_type,
                            d.source,
                            d.corp_code,
                            d.stock_code,
                            d.title,
                            d.url,
                            d.published_at
                        from rag_chunks c
                        join rag_documents d on d.id = c.document_id
                        where d.source_type = %s
                          and (%s::text is null or d.stock_code = %s::text)
                          and (%s::text is null or d.corp_code = %s::text)
                    ),
                    vector_hits as (
                        select
                            id,
                            row_number() over (order by embedding <=> %s::vector) as vector_rank,
                            1 - (embedding <=> %s::vector) as similarity
                        from filtered_chunks
                        where embedding is not null
                        order by embedding <=> %s::vector
                        limit %s::int
                    ),
                    keyword_hits as (
                        select
                            id,
                            row_number() over (
                                order by ts_rank_cd(search_tsv, plainto_tsquery('simple', %s)) desc
                            ) as keyword_rank,
                            ts_rank_cd(search_tsv, plainto_tsquery('simple', %s)) as keyword_score
                        from filtered_chunks
                        where search_tsv @@ plainto_tsquery('simple', %s)
                        order by keyword_score desc
                        limit %s::int
                    ),
                    fused_hits as (
                        select
                            coalesce(v.id, kw.id) as id,
                            v.vector_rank,
                            kw.keyword_rank,
                            v.similarity,
                            kw.keyword_score,
                            coalesce(1.0 / (%s + v.vector_rank), 0)
                                + coalesce(1.0 / (%s + kw.keyword_rank), 0) as rrf_score
                        from vector_hits v
                        full outer join keyword_hits kw on kw.id = v.id
                    )
                    select
                        c.id,
                        c.stock_code,
                        c.corp_code,
                        c.title,
                        c.content as body,
                        c.url as source_url,
                        c.source as publisher,
                        c.published_at,
                        c.source_type,
                        f.similarity,
                        f.keyword_score,
                        f.rrf_score,
                        f.vector_rank,
                        f.keyword_rank,
                        'hybrid_rrf' as retrieval_method
                    from fused_hits f
                    join filtered_chunks c on c.id = f.id
                    order by
                        f.rrf_score desc,
                        f.similarity desc nulls last,
                        f.keyword_score desc nulls last,
                        c.published_at desc nulls last
                    limit %s::int
                    """,
                    (
                        source_type,
                        stock_code,
                        stock_code,
                        corp_code,
                        corp_code,
                        query_embedding,
                        query_embedding,
                        query_embedding,
                        candidate_limit,
                        query,
                        query,
                        query,
                        candidate_limit,
                        RRF_K,
                        RRF_K,
                        k,
                    ),
                )

                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
    except Exception:
        # DB or vector index may be unavailable in test/dev environments.
        # Return empty evidence set and let callers handle absence gracefully.
        return []

    return _rows_to_dicts(columns, rows)


def retrieve_news(ticker: str | None, query: str, k: int = 5) -> list[dict[str, Any]]:
    return _hybrid_search(source_type="news", stock_code=ticker, query=query, k=k)


def retrieve_disclosures(corp_code: str | None, query: str, k: int = 5) -> list[dict[str, Any]]:
    return _hybrid_search(source_type="disclosure", corp_code=corp_code, query=query, k=k)
