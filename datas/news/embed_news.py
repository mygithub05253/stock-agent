from __future__ import annotations

import json
import os
import time
from typing import Any, Iterable

import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 100


def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL)


def split_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[str]:
    if not text:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be greater than or equal to 0 and smaller than chunk_size")

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap

    while start < len(text):
        chunk = text[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += step

    return chunks


def fetch_rag_documents(cursor, limit: int = 1000) -> list[tuple[Any, ...]]:
    cursor.execute(
        """
        SELECT
            id,
            source_type,
            source,
            external_id,
            corp_code,
            stock_code,
            title,
            content,
            published_at,
            metadata
        FROM rag_documents
        WHERE source_type = 'news'
          AND content IS NOT NULL
          AND btrim(content) <> ''
        ORDER BY published_at DESC NULLS LAST, updated_at DESC
        LIMIT %s;
        """,
        (limit,),
    )
    return cursor.fetchall()


def normalize_embedding(embedding: Any) -> list[float]:
    values = embedding.tolist() if hasattr(embedding, "tolist") else embedding
    return [float(value) for value in values]


def build_chunk_metadata(
    *,
    document_metadata: Any,
    source: str,
    external_id: str | None,
    title: str | None,
    published_at: Any,
) -> dict[str, Any]:
    if isinstance(document_metadata, str):
        try:
            document_metadata = json.loads(document_metadata)
        except json.JSONDecodeError:
            document_metadata = {"raw_metadata": document_metadata}
    elif document_metadata is None:
        document_metadata = {}

    return {
        **document_metadata,
        "source": source,
        "external_id": external_id,
        "title": title,
        "published_at": published_at.isoformat() if hasattr(published_at, "isoformat") else published_at,
        "embedding_model": EMBEDDING_MODEL,
        "embedder": "datas/news/embed_news.py",
    }


def upsert_chunk(
    cursor,
    *,
    document_id: str,
    chunk_index: int,
    chunk_text: str,
    embedding: list[float],
    metadata: dict[str, Any],
) -> None:
    cursor.execute(
        """
        INSERT INTO rag_chunks (
            document_id,
            chunk_index,
            content,
            token_count,
            embedding,
            embedding_model,
            metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (document_id, chunk_index, embedding_model)
        DO UPDATE SET
            content = EXCLUDED.content,
            token_count = EXCLUDED.token_count,
            embedding = EXCLUDED.embedding,
            metadata = EXCLUDED.metadata;
        """,
        (
            document_id,
            chunk_index,
            chunk_text,
            len(chunk_text.split()),
            embedding,
            EMBEDDING_MODEL,
            json.dumps(metadata, ensure_ascii=False),
        ),
    )


def delete_stale_chunks(cursor, *, document_id: str, valid_chunk_count: int) -> None:
    cursor.execute(
        """
        DELETE FROM rag_chunks
        WHERE document_id = %s
          AND embedding_model = %s
          AND chunk_index >= %s;
        """,
        (document_id, EMBEDDING_MODEL, valid_chunk_count),
    )


def embed_document_chunks(
    cursor,
    model: SentenceTransformer,
    row: tuple[Any, ...],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> int:
    (
        document_id,
        _source_type,
        source,
        external_id,
        _corp_code,
        _stock_code,
        title,
        content,
        published_at,
        document_metadata,
    ) = row

    chunks = split_text(content, chunk_size=chunk_size, overlap=overlap)
    metadata = build_chunk_metadata(
        document_metadata=document_metadata,
        source=source,
        external_id=external_id,
        title=title,
        published_at=published_at,
    )

    for chunk_index, chunk_text in enumerate(chunks):
        embedding = normalize_embedding(model.encode(chunk_text))
        upsert_chunk(
            cursor,
            document_id=document_id,
            chunk_index=chunk_index,
            chunk_text=chunk_text,
            embedding=embedding,
            metadata={**metadata, "chunk_index": chunk_index},
        )

    delete_stale_chunks(cursor, document_id=document_id, valid_chunk_count=len(chunks))
    return len(chunks)


def embed_documents(
    cursor,
    model: SentenceTransformer,
    documents: Iterable[tuple[Any, ...]],
    *,
    commit_every: int = 50,
    conn=None,
) -> int:
    total_chunks = 0

    for idx, row in enumerate(documents, start=1):
        chunk_count = embed_document_chunks(cursor, model, row)
        total_chunks += chunk_count

        if conn is not None and idx % commit_every == 0:
            conn.commit()
            print(f"  -> {idx} documents processed...")

    return total_chunks


def embed_news(limit: int = 1000) -> None:
    print("뉴스 RAG 임베딩 파이프라인 시작...")

    if not DATABASE_URL:
        print("DATABASE_URL 누락")
        return

    conn = None
    cursor = None

    try:
        conn = psycopg2.connect(DATABASE_URL)
        register_vector(conn)
        cursor = conn.cursor()

        documents = fetch_rag_documents(cursor, limit=limit)
        if not documents:
            print("임베딩할 뉴스 rag_documents가 없습니다.")
            return

        print(f"임베딩 대상 뉴스 문서: {len(documents)}건")
        model = get_embedding_model()
        total_chunks = embed_documents(cursor, model, documents, conn=conn)
        conn.commit()

        print(f"뉴스 RAG 임베딩 완료: 총 {total_chunks}개 chunk 저장")

    except Exception as exc:
        if conn is not None:
            conn.rollback()
        print(f"뉴스 RAG 임베딩 실패: {exc.__class__.__name__}: {exc}")
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    time.sleep(0.05)


if __name__ == "__main__":
    embed_news()
