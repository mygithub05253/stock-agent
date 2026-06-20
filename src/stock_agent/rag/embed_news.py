from __future__ import annotations

from datas.news.embed_news import embed_news


def embed_raw_news(limit: int = 1000) -> None:
    """Backward-compatible entrypoint for the current rag_documents -> rag_chunks pipeline."""
    embed_news(limit=limit)


if __name__ == "__main__":
    embed_raw_news()
