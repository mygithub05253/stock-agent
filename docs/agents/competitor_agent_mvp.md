# Competitor Agent MVP 설명서

## 개요

| 항목 | 내용 |
|------|------|
| 목적 | 국내 같은 섹터 peer를 선정하고 대상 종목의 상대적 위치와 비교 근거를 계산합니다. |
| 주요 파일 | `src/stock_agent/agents/competitor.py`, `src/stock_agent/tools/peer_tool.py`, `src/stock_agent/schemas/analysis.py`, `src/stock_agent/prompts/competitor/system.md` |
| 사용 DB | `company`, `stock_price`, `financial_statement` |
| LLM 사용 여부 | MVP 계산은 LLM 없이 Python/tool 결과만 사용합니다. 시스템 프롬프트는 향후 LLM 요약 단계에서 도구 결과를 해석할 때 사용합니다. |

Competitor Agent는 Curator가 확정한 종목을 기준으로 국내 같은 섹터의 peer를 찾고, 가격 데이터와 재무 데이터를 이용해 상대 비교 점수를 만듭니다. 결과는 `CompetitorResult`로 반환되어 Strategist가 종합 판단에 사용합니다.

DB 연결이나 조회가 실패하면 `mock_data_fallback` 결과를 반환합니다. 이는 데모 흐름이 끊기지 않게 하는 대체 경로이며, 실제 투자 분석용 DB 결과가 아닙니다.

## 동작 흐름

1. Curator Agent가 대상 종목의 `stock_code`, `corp_code`, `sector`를 확정합니다.
2. `run_competitor(state)`가 `state.curator` 존재 여부를 확인합니다. 없으면 오류를 냅니다.
3. DB 연결을 열고 `peer_tool.build_peer_comparison()`을 호출합니다.
4. `company` 테이블에서 대상 기업을 조회하고, 같은 섹터의 peer 후보를 가져옵니다. 대상 기업에 섹터가 없고 Curator가 섹터를 제공하면 그 값을 사용합니다.
5. `stock_price`에서 최신 종가, 시가총액, 거래량을 가져오고, `financial_statement`에서 최근 재무 snapshot과 직전 연도 snapshot을 가져옵니다.
6. PER, PBR, ROE, 매출 성장률, 영업이익률, 부채비율, 데이터 품질 점수를 계산한 뒤 데이터 품질과 시가총액 근접도 기준으로 최종 peer를 선택합니다.
7. 상대 위치, evidence, 경고, `score`, peer 목록을 `CompetitorResult`로 변환해 Strategist가 사용할 수 있게 반환합니다.

## Score 해석 방법

`score`는 0~100 사이의 상대 비교 점수입니다. 50점은 peer 대비 중립에 가까운 위치로 해석합니다.

현재 MVP의 가중치는 다음과 같습니다.

| 구성 요소 | 가중치 | 해석 방향 |
|-----------|--------|-----------|
| Valuation position | 20% | PER, PBR이 낮을수록 보수적으로 유리하게 반영 |
| Profitability position | 25% | ROE가 높을수록 긍정적으로 반영 |
| Growth position | 20% | 매출 성장률이 높을수록 긍정적으로 반영 |
| Margin position | 15% | 영업이익률이 높을수록 긍정적으로 반영 |
| Balance sheet position | 10% | 부채비율이 낮을수록 긍정적으로 반영 |
| Data quality | 10% | 대상 종목의 핵심 데이터가 많이 채워질수록 긍정적으로 반영 |

주의할 점은 다음과 같습니다.

- peer가 3개 미만이면 `peer_count_below_minimum` 경고가 붙고 점수가 감점됩니다.
- 대상 종목의 데이터 품질 점수가 낮으면 `target_data_quality_low` 경고가 붙고 점수가 보수적으로 제한됩니다.
- PER/PBR/ROE/매출 성장률/영업이익률/부채비율 중 계산할 수 없는 값은 결측으로 남기며, LLM이나 문서에서 임의로 채우면 안 됩니다.
- `warnings`와 `data_quality_flags`가 있으면 점수보다 경고를 먼저 확인해야 합니다.

## MVP 제외 범위

- 글로벌 peer 자동 추가
- LLM을 이용한 기업명, 지표, 수치 추정
- Streamlit 상세 화면 구현
- 분석 결과 캐시 저장
- `analysis_history` 같은 영구 이력 저장
- 직접적인 매수, 매도, 보유 권고 생성
- 외부 실시간 데이터 API 연동

## UI 연결 아이디어

- Tier 2의 Peer 비교 섹션에 `peer_summary`와 `score`를 함께 표시합니다.
- peer 표에는 `corp_name`, `stock_code`, `sector`, `per`, `pbr`, `roe`, `revenue_growth`, `operating_margin`, `debt_ratio`, `data_quality_score`를 표시합니다.
- `warnings`나 `data_quality_flags`가 있으면 표 상단에 데이터 품질 배지로 노출합니다.
- `relative_position`은 작은 막대나 percentile 텍스트로 보여주면 PM과 사용자가 상대 위치를 빠르게 이해할 수 있습니다.
- `a1_peer_multiple_payload`의 `median_per`, `median_pbr`는 향후 A1 peer multiple 설명 영역과 연결할 수 있습니다.
- `mock_data_fallback`이 있으면 결과 전체에 "데모 대체 데이터" 경고를 표시합니다.

## 변경 이력

| 날짜 | 요약 |
|------|------|
| 2026-05-27 | Competitor Agent MVP 문서 최초 작성 |
