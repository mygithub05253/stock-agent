from stock_agent.rag import retriever


class FakeEmbedding:
    def encode(self, query: str) -> list[float]:
        assert query
        return [0.1, 0.2, 0.3]


class FakeCursor:
    def __init__(self) -> None:
        self.description = [
            ("id",),
            ("stock_code",),
            ("corp_code",),
            ("title",),
            ("body",),
            ("source_url",),
            ("publisher",),
            ("published_at",),
            ("source_type",),
            ("similarity",),
            ("keyword_score",),
            ("rrf_score",),
            ("vector_rank",),
            ("keyword_rank",),
            ("retrieval_method",),
        ]
        self.query = ""
        self.params = ()

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple) -> None:
        self.query = query
        self.params = params

    def fetchall(self) -> list[tuple]:
        return [
            (
                "chunk-1",
                "005930",
                "00126380",
                "AI semiconductor demand improves",
                "Samsung earnings outlook improves on AI chip demand.",
                "https://example.com/news",
                "example",
                None,
                "news",
                0.91,
                0.42,
                0.031,
                1,
                2,
                "hybrid_rrf",
            )
        ]


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.cursor_obj = cursor

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self.cursor_obj


def patch_retriever(monkeypatch, cursor: FakeCursor) -> None:
    monkeypatch.setattr(retriever, "get_embedding_model", lambda: FakeEmbedding())
    monkeypatch.setattr(retriever, "register_vector", lambda conn: None)
    monkeypatch.setattr(retriever, "get_connection", lambda: FakeConnection(cursor))


def test_retrieve_news_uses_hybrid_rrf_over_rag_chunks(monkeypatch):
    cursor = FakeCursor()
    patch_retriever(monkeypatch, cursor)

    docs = retriever.retrieve_news(ticker="005930", query="AI semiconductor earnings", k=3)

    assert docs[0]["retrieval_method"] == "hybrid_rrf"
    assert docs[0]["rrf_score"] == 0.031
    assert "rag_chunks" in cursor.query
    assert "rag_documents" in cursor.query
    assert "plainto_tsquery" in cursor.query
    assert "ts_rank_cd" in cursor.query
    assert "rrf_score" in cursor.query
    assert "news_chunks" not in cursor.query
    assert "news" in cursor.params
    assert "005930" in cursor.params


def test_retrieve_disclosures_uses_corp_code_filter(monkeypatch):
    cursor = FakeCursor()
    patch_retriever(monkeypatch, cursor)

    docs = retriever.retrieve_disclosures(
        corp_code="00126380",
        query="recent business report risks",
        k=2,
    )

    assert docs[0]["retrieval_method"] == "hybrid_rrf"
    assert "rag_chunks" in cursor.query
    assert "rag_documents" in cursor.query
    assert "disclosure" in cursor.params
    assert "00126380" in cursor.params
