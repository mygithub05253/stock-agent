import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "datas" / "news" / "embed_news.py"
SPEC = importlib.util.spec_from_file_location("news_embed_pipeline", MODULE_PATH)
news_embed = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(news_embed)


class FakeModel:
    def encode(self, text: str) -> list[float]:
        assert text
        return [0.1, 0.2, 0.3]


class FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple]] = []

    def execute(self, query: str, params: tuple) -> None:
        self.executed.append((query, params))

    def fetchall(self) -> list[tuple]:
        return []


def test_fetch_rag_documents_uses_current_rag_document_schema():
    cursor = FakeCursor()

    news_embed.fetch_rag_documents(cursor, limit=10)

    query, params = cursor.executed[0]
    assert "SELECT" in query
    assert " id," in query
    assert "FROM rag_documents" in query
    assert "source_type = 'news'" in query
    assert "document_id" not in query
    assert params == (10,)


def test_embed_document_chunks_upserts_embeddings_into_rag_chunks(monkeypatch):
    monkeypatch.setattr(news_embed, "EMBEDDING_MODEL", "BAAI/bge-m3")
    cursor = FakeCursor()
    row = (
        "doc-1",
        "news",
        "naver_finance",
        "external-1",
        "00126380",
        "005930",
        "Samsung AI demand",
        "AI chip demand is improving. Earnings expectations are rising.",
        None,
        {"event_type": "industry_trend"},
    )

    chunk_count = news_embed.embed_document_chunks(
        cursor,
        FakeModel(),
        row,
        chunk_size=30,
        overlap=5,
    )

    assert chunk_count >= 2
    insert_queries = [query for query, _params in cursor.executed if "INSERT INTO rag_chunks" in query]
    assert insert_queries
    insert_query = insert_queries[0]
    assert "embedding" in insert_query
    assert "embedding_model" in insert_query
    assert "metadata" in insert_query
    assert "published_at" not in insert_query
    assert "stock_code" not in insert_query
    assert "corp_code" not in insert_query
    assert "updated_at" not in insert_query

    first_insert_params = cursor.executed[0][1]
    assert first_insert_params[0] == "doc-1"
    assert first_insert_params[4] == [0.1, 0.2, 0.3]
    assert first_insert_params[5] == "BAAI/bge-m3"

    delete_query, delete_params = cursor.executed[-1]
    assert "DELETE FROM rag_chunks" in delete_query
    assert delete_params == ("doc-1", "BAAI/bge-m3", chunk_count)
