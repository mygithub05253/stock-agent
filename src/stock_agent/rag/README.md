# `src/stock_agent/rag/` — RAG 검색 컴포넌트

뉴스·공시 텍스트를 임베딩→검색→재정렬하는 모듈입니다. 부트캠프 W1 학습이 가장 직접적으로 적용되는 영역.

## 파일

| 파일 | 역할 | 라이브러리 |
|------|------|-----------|
| `chroma_store.py` | Chroma 벡터 DB 인덱싱·검색 | chromadb |
| `embedding.py` | 한국어 임베딩 모델 (BGE-m3 또는 Solar Embedding) | sentence-transformers |
| `retriever.py` | Hybrid Search (BM25 + Vector) | rank_bm25 + chroma |
| `reranker.py` | 검색 결과 재정렬 (BGE-reranker) | sentence-transformers |

## 데이터 흐름

```
[원본 텍스트] → embedding.py → [벡터] → chroma_store.py 적재
                                            ↓
사용자 쿼리 → retriever.py (Hybrid) → reranker.py → 최종 N개 청크 반환
```

## 작업 규칙

- 정형 데이터(회원·재무·시세)는 Postgres, 비정형(뉴스·공시 본문 + 임베딩)은 Chroma — 데이터 아키텍처 B안 (`docs/decisions/ADR-001-data-arch.md` 참조)
- 청킹 사이즈 기본 512 token. 변경 시 평가 하네스 재실행 필수.
