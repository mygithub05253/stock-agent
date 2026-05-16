CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS rag_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type TEXT NOT NULL CHECK (source_type IN ('news', 'disclosure', 'report', 'macro', 'other')),
    source TEXT NOT NULL,
    external_id TEXT,
    corp_code VARCHAR(8),
    stock_code VARCHAR(6),
    title TEXT,
    url TEXT,
    published_at TIMESTAMPTZ,
    content TEXT NOT NULL,
    content_hash TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (corp_code) REFERENCES company(corp_code) ON DELETE SET NULL,
    FOREIGN KEY (stock_code) REFERENCES company(stock_code) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_rag_documents_external
    ON rag_documents (source_type, source, external_id)
    WHERE external_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_rag_documents_stock_published
    ON rag_documents (stock_code, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_rag_documents_metadata
    ON rag_documents USING GIN (metadata);

COMMENT ON TABLE rag_documents IS 'RAG용 뉴스·공시·리포트 원문 저장 테이블';
COMMENT ON COLUMN rag_documents.source_type IS 'news, disclosure, report 등 문서 유형';
COMMENT ON COLUMN rag_documents.content IS '정제된 원문 텍스트';

CREATE TABLE IF NOT EXISTS rag_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    token_count INT,
    embedding vector(1024),
    embedding_model TEXT NOT NULL DEFAULT 'bge-m3',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    search_tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (document_id) REFERENCES rag_documents(id) ON DELETE CASCADE,
    CONSTRAINT uk_rag_chunk UNIQUE (document_id, chunk_index, embedding_model)
);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_document
    ON rag_chunks (document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_metadata
    ON rag_chunks USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_search_tsv
    ON rag_chunks USING GIN (search_tsv);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_content_trgm
    ON rag_chunks USING GIN (content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding_cosine
    ON rag_chunks USING hnsw (embedding vector_cosine_ops);

COMMENT ON TABLE rag_chunks IS 'Postgres pgvector 기반 RAG 청크와 임베딩 저장 테이블';
COMMENT ON COLUMN rag_chunks.embedding IS '기본 1024차원 임베딩 벡터. 모델 변경 시 마이그레이션 필요';
