# `src/stock_agent/tools/` — 외부 데이터 Tool

LangChain `@tool` 데코레이터로 등록되는 외부 데이터 호출 함수들.

## 파일

| 파일 | Tool | 데이터 |
|------|------|--------|
| `dart_tool.py` | `get_company_info`, `get_financial_5y`, `get_disclosures` | DART API |
| `pykrx_tool.py` | `get_price_ohlcv`, `get_market_cap`, `get_listing` | pykrx |
| `news_tool.py` | `crawl_naver_news`, `search_news_rag` | 네이버금융 + Postgres pgvector |
| `macro_tool.py` | `get_ecos_rate`, `get_fred_macro` | ECOS + FRED |

## 작업 규칙

- Tool은 **순수 함수** (사이드 이펙트는 캐싱·로깅만)
- 외부 API 호출은 **반드시 캐시 우선** (`scripts/cache_warmup.py` 참조)
- API 키는 `.env` 에서만 로드. 코드 하드코딩 금지.
- Tool 호출 결과는 향후 LangSmith와 Postgres 분석 로그에 기록.
