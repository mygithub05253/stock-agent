# `src/stock_agent/tools/` — 데이터 조회와 계산 Tool

이 폴더는 agent가 사용하는 DB 조회, 외부 API 호출, 계산 함수를 담습니다. `agents/`에는 판단 흐름을 두고, `tools/`에는 데이터 접근과 계산을 둡니다.

## 목표 파일 구조

| 파일 | 기능 | 사용 Agent |
|------|------|------------|
| `company_tool.py` | 종목 검색, `stock_code`/`corp_code` 조회 | Curator, Competitor |
| `price_tool.py` | 최근 가격, 가격 히스토리, 모멘텀 계산 | Quant, Competitor |
| `financial_tool.py` | 재무제표 조회, PER/PBR/ROE, valuation 계산 | Quant, Competitor |
| `rag_tool.py` | 뉴스/공시 chunk 검색, source bundle 반환 | Qual |
| `peer_tool.py` | 동종업계 peer 선정, 비교 지표 생성 | Competitor |
| `macro_tool.py` | 금리/환율/경기 context 생성 | Quant, Strategist |
| `cache_tool.py` | 분석 캐시 조회/저장 | Pipeline, Strategist |

## 작업 규칙

- Tool은 가능한 **순수 함수** 로 작성합니다. 사이드 이펙트는 캐싱과 로깅으로 제한합니다.
- 외부 API 호출은 **반드시 캐시 우선** 으로 설계합니다.
- API 키는 `.env` 에서만 로드. 코드 하드코딩 금지.
- Tool 호출 결과는 향후 LangSmith와 Postgres 분석 로그에 기록합니다.
- Tool output은 agent가 바로 사용할 수 있도록 Pydantic schema 또는 명확한 dict 구조로 반환합니다.
- 금융 계산은 LLM이 아니라 Tool에서 처리합니다.

## 현재 상태

현재 `tools/`에는 구현 파일이 아직 없고 README만 있습니다. Phase 1 agent는 mock 데이터를 직접 반환합니다. 다음 단계에서는 `Quant`부터 `price_tool.py`, `financial_tool.py`를 연결하는 것이 우선입니다.
