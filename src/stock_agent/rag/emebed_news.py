import chromadb
from sentence_transformers import SentenceTransformer


def embed_news_documents(news_docs: list[dict]) -> None:
    model = SentenceTransformer("BAAI/bge-m3")

    client = chromadb.PersistentClient(path="./chroma")
    collection = client.get_or_create_collection(name="news_chunks")

    documents = []
    metadatas = []
    ids = []

    for idx, doc in enumerate(news_docs):
        text = doc["body"]
        embedding = model.encode(text).tolist()

        documents.append(text)
        metadatas.append(
            {
                "stock_code": doc.get("stock_code", ""),
                "title": doc.get("title", ""),
                "source_url": doc.get("url", ""),
                "crawled_at": doc.get("crawled_at", ""),
                "event_type": doc.get("event_type", "unknown"),
            }
        )
        ids.append(f"news-{idx}")

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=[
            model.encode(doc).tolist()
            for doc in documents
        ],
    )


if __name__ == "__main__":
    sample_news = [
        {
            "stock_code": "005930",
            "title": "삼성전자 AI 반도체 수요 회복 기대",
            "body": "AI 서버 투자 확대에 따라 고대역폭 메모리 수요가 증가하고 있습니다.",
            "url": "https://example.com/news/1",
            "crawled_at": "2026-05-28",
            "event_type": "industry_trend",
        }
    ]

    embed_news_documents(sample_news)