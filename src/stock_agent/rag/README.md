# `src/stock_agent/rag/` - Qual RAG Retrieval

This package provides the retrieval path used by the Qual Agent.

## Current Path

```text
datas/news/news_collector.py
  -> raw_news
  -> rag_documents

datas/news/embed_news.py
  -> rag_chunks.content
  -> rag_chunks.embedding

src/stock_agent/rag/retriever.py
  -> vector search + keyword search
  -> RRF fusion
  -> optional CrossEncoder reranking
  -> Qual Agent evidence
```

## Files

| File | Role |
| --- | --- |
| `retriever.py` | Primary Hybrid/RRF retriever for news and disclosures. |
| `embed_news.py` | Backward-compatible wrapper that calls `datas/news/embed_news.py`. It no longer writes to legacy `news_chunks`. |
| `pgvector_store.py` | Low-level vector diagnostic helper. The Qual Agent does not use this as its primary path. |

## Reranker

The primary retriever can rerank Hybrid/RRF candidates with a CrossEncoder.

```powershell
$env:RAG_RERANKER_ENABLED="true"
$env:RAG_RERANKER_MODEL="BAAI/bge-reranker-v2-m3"
```

Default behavior keeps reranking disabled so local tests and demos do not load the reranker model unless explicitly requested.

## Retriever Evaluation

Run the lightweight retriever quality harness against the configured DB:

```powershell
python eval/run_rag_retriever_eval.py --k 5
```

The script writes a report to `eval/reports/YYYY-MM-DD_rag_retriever_eval.json` with Hit@K, MRR, and nDCG@K.

## Tests

```powershell
python -m pytest tests/rag -q
```
