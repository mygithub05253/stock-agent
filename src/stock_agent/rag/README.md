# `src/stock_agent/rag/` — RAG 검색 컴포넌트

뉴스·공시 텍스트를 임베딩→검색→재정렬하는 모듈입니다. 기본 저장소는 Postgres + pgvector입니다.

## 파일

| 파일 | 역할 | 라이브러리 |
|------|------|-----------|
| `pgvector_store.py` | Postgres pgvector 유사도 검색 | psycopg + pgvector |
| `embedding.py` | 한국어 임베딩 모델 (BGE-m3 또는 Solar Embedding) | sentence-transformers |
| `retriever.py` | Hybrid Search (keyword + vector) | Postgres GIN + pgvector |
| `reranker.py` | 검색 결과 재정렬 (BGE-reranker) | sentence-transformers |
| `chroma_store.py` | 향후 선택 가능한 Chroma adapter | chromadb |

## 데이터 흐름

```
[원본 텍스트] → embedding.py → [벡터] → rag_documents / rag_chunks 적재
                                            ↓
사용자 쿼리 → retriever.py (Hybrid) → reranker.py → 최종 N개 청크 반환
```

## 작업 규칙

- 정형 데이터와 RAG 데이터 모두 Postgres에 저장합니다. 임베딩 검색은 pgvector를 사용합니다.
- Chroma는 삭제하지 않고 향후 optional backend로 추가할 수 있게 이름만 예약합니다.
- 청킹 사이즈 기본 512 token. 변경 시 평가 하네스 재실행 필수.
