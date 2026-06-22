# `tests/rag/` - RAG 파이프라인 검증

> 뉴스 임베딩 입력 변환과 PostgreSQL/pgvector Hybrid Search 계약을 검증합니다.

## 핵심 범위

- 원천 뉴스에서 임베딩 텍스트 선택
- 뉴스 metadata와 청크 적재 형태
- 키워드·벡터 검색 결과 병합
- 종목 코드와 source type 필터
- DB·모델 의존성은 monkeypatch로 격리

## 기술 스택과 동작

pytest, sentence-transformers, psycopg, pgvector를 사용합니다. 모듈 import 단계에서 임베딩 패키지를 읽으므로 Python 환경의 `transformers`, `huggingface_hub`, `tqdm` 호환성이 필요합니다.

## 실행

```bash
python -m pytest tests/rag -v
```

## 구조

| 파일 | 검증 대상 |
|------|-----------|
| `test_news_embedding_pipeline.py` | 임베딩 입력·적재 |
| `test_retriever.py` | Hybrid Search와 필터 |
