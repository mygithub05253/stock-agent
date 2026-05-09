CREATE TABLE IF NOT EXISTS raw_news (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT,
    title TEXT,
    published_at TIMESTAMPTZ,
    payload JSONB NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source, external_id)
);

CREATE TABLE IF NOT EXISTS raw_macro (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    indicator_code TEXT NOT NULL,
    observed_at DATE,
    payload JSONB NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source, indicator_code, observed_at)
);

CREATE TABLE IF NOT EXISTS raw_dart (
    id BIGSERIAL PRIMARY KEY,
    corp_code TEXT NOT NULL,
    stock_code TEXT,
    report_code TEXT,
    report_name TEXT,
    reported_at DATE,
    payload JSONB NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (corp_code, report_code, reported_at)
);

CREATE INDEX IF NOT EXISTS idx_raw_news_published_at ON raw_news (published_at);
CREATE INDEX IF NOT EXISTS idx_raw_macro_indicator_observed_at ON raw_macro (indicator_code, observed_at);
CREATE INDEX IF NOT EXISTS idx_raw_dart_stock_reported_at ON raw_dart (stock_code, reported_at);
