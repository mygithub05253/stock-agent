# `src/stock_agent/rag/` — RAG 검색 컴포넌트

뉴스·공시 텍스트를 임베딩→검색→재정렬하는 모듈입니다. 기본 저장소는 Postgres + pgvector입니다.

## 파일

| 파일 | 역할 | 라이브러리 |
|------|------|-----------|
| `pgvector_store.py` | Postgres pgvector 유사도 검색 | psycopg + pgvector |
| `embedding.py` | 후속 예정. 한국어 임베딩 모델 (BGE-m3 또는 Solar Embedding) | sentence-transformers 등 |
| `retriever.py` | 후속 예정. Hybrid Search (keyword + vector) | Postgres GIN + pgvector |
| `reranker.py` | 후속 예정. 검색 결과 재정렬 | sentence-transformers 등 |
| `chroma_store.py` | 후속 optional. Chroma adapter | chromadb |

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
- Qual Agent는 검색된 chunk에 없는 사실을 생성하지 않습니다.
- 반환 결과에는 `document_id`, `title`, `url`, `published_at`, `stock_code`, `score`를 포함해 evidence 추적이 가능해야 합니다.
- 검색 품질 평가는 최소 `Source Attachment Rate`, `RAG Faithfulness`, `Top-k relevance`를 봅니다.

## 우선 연결 작업

1. `Qual Agent`에서 `search_similar_chunks()` 호출
2. 검색 결과를 `QualResult.evidence`와 향후 `sources` 필드에 연결
3. RAG 결과가 비어 있을 때 `warnings`에 근거 부족 표시
4. `Guardrail`에서 출처 없는 정성 근거를 warning 처리
