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



CREATE INDEX IF NOT EXISTS idx_raw_news_published_at ON raw_news (published_at);
CREATE INDEX IF NOT EXISTS idx_raw_macro_indicator_observed_at ON raw_macro (indicator_code, observed_at);



-- 1. company (기업 기본 정보 Master)
CREATE TABLE IF NOT EXISTS company (
    corp_code VARCHAR(8) PRIMARY KEY,
    stock_code VARCHAR(6) UNIQUE,
    corp_name VARCHAR(100) NOT NULL,
    sector VARCHAR(50),
    listing_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE company IS '대한민국 상장사 기본 마스터 정보 테이블';
COMMENT ON COLUMN company.corp_code IS 'DART에서 사용하는 8자리 고유법인코드';
COMMENT ON COLUMN company.stock_code IS '한국거래소(KRX) 6자리 상장 종목코드';

-- 2. stock_price (일별 시세 데이터 Fact)
CREATE TABLE IF NOT EXISTS stock_price (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL,
    base_date DATE NOT NULL,
    close_price INT NOT NULL,
    market_cap BIGINT,
    volume BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (stock_code) REFERENCES company(stock_code) ON DELETE CASCADE,
    CONSTRAINT uk_stock_price UNIQUE (stock_code, base_date)
);

CREATE INDEX IF NOT EXISTS idx_stock_price_search ON stock_price (stock_code, base_date DESC);
COMMENT ON TABLE stock_price IS '기업별 일별 주가 및 시가총액 시계열 기록 테이블';


-- 3. financial_statement (핵심 재무 수치 Fact)
CREATE TABLE IF NOT EXISTS financial_statement (
    id BIGSERIAL PRIMARY KEY,
    corp_code VARCHAR(8) NOT NULL,
    bsns_year INT NOT NULL,
    reprt_code VARCHAR(5) NOT NULL,
    fs_div VARCHAR(3) NOT NULL, 
    account_nm VARCHAR(100) NOT NULL,
    amount BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (corp_code) REFERENCES company(corp_code) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_fs_search ON financial_statement (corp_code, bsns_year, account_nm);
COMMENT ON TABLE financial_statement IS 'AI 에이전트 수치 계산용 핵심 재무제표 테이블';

-- 4. disclosure_report (공시 메타데이터 Index)
CREATE TABLE IF NOT EXISTS disclosure_report (
    rcept_no VARCHAR(14) PRIMARY KEY,
    corp_code VARCHAR(8) NOT NULL,
    report_nm VARCHAR(200) NOT NULL,
    rcept_dt DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (corp_code) REFERENCES company(corp_code) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_report_date ON disclosure_report (corp_code, rcept_dt DESC);
COMMENT ON TABLE disclosure_report IS 'DART 전자공시 시스템 등록 보고서 목차 테이블';

-- 5. disclosure_content (공시 원본 텍스트 및 요약 Content)
CREATE TABLE IF NOT EXISTS disclosure_content (
    rcept_no VARCHAR(14) PRIMARY KEY,
    content TEXT, -- PostgreSQL에서는 TEXT가 무제한 용량을 지원하므로 LONGTEXT 대신 TEXT를 씁니다.
    summary TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (rcept_no) REFERENCES disclosure_report(rcept_no) ON DELETE CASCADE
);

COMMENT ON TABLE disclosure_content IS 'RAG 및 자연어 분석용 비정형 공시 원문 저장 테이블';