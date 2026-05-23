# 기능 명세서 v0.2 - 포트폴리오 일괄 안내 기능

| 항목 | 값 |
|------|-----|
| 작성자 | PM |
| 작성일 | 2026-05-23 |
| 버전 | v0.2 |
| 상위 문서 | `docs/prd/PRD_v0.6.md` |
| 참조 문서 | `docs/functional-spec/overview/functional_spec_all_features_v0.1.md`, `docs/operations/llm_cost_guide.md`, `docs/architecture/erd.md` |
| 대상 사용자 | 개발자 + PM + 데이터팀 |
| 기능 ID | `F-BULK-01` |

---

## 0. 문서 메타 정보

본 문서는 기존 `overview/functional_spec_all_features_v0.1.md`의 7대 표준 양식인 **트리거 / 전제조건 / 입력 / 처리 흐름 / 출력 / 예외 처리 / 담당**을 유지하면서, 신규 기능인 **포트폴리오 일괄 안내 기능**의 상세 동작을 정의한다.

`F-BULK-01`은 여러 보유 종목을 한 번에 분석하므로, 단일 종목 분석보다 **LLM 비용 폭발**, **외부 API 타임아웃**, **Streamlit UI 멈춤**, **부분 실패 처리** 위험이 크다. 따라서 본 명세는 24시간 Postgres 캐시 우선 조회, 종목 수 기반 Batch 처리, 비용 임계점 가드레일을 핵심 제약으로 둔다.

---

## 1. 문서 위치 / 작성 원칙

| 원칙 | 적용 방식 |
|------|-----------|
| Markdown 콘텐츠와 HTML 대시보드 분리 | 본 문서는 기능 명세 콘텐츠이며, 향후 대시보드는 별도 HTML로 작성 |
| 프롬프트와 코드 분리 | 프롬프트 본문은 코드에 쓰지 않고 `src/stock_agent/prompts/` 또는 `docs/` 하위 문서로 분리 |
| 7대 표준 양식 준수 | 기능별로 트리거, 전제조건, 입력, 처리 흐름, 출력, 예외 처리, 담당을 고정 순서로 작성 |
| 테이블화 | 입력, 출력, 담당, KPI, 비용 기준은 표로 정리 |
| 비용 상한 명시 | 월 LLM 비용 5만원 상한을 기능 제약으로 포함 |
| 에지 케이스 명시 | 데이터 결손, LLM 실패, 비용 임계점, API 타임아웃, 대량 보유 종목을 예외 처리에 포함 |

---

## 2. 기능 개요

포트폴리오 일괄 안내 기능은 로그인한 사용자가 보유한 여러 종목을 한 번에 분석하여, 종목별 투자 안내와 포트폴리오 차원의 요약 리스크를 제공하는 기능이다.

MVP에서는 각 보유 종목에 대해 가능한 범위의 정량 데이터, 정성 데이터, Peer 정보, 기존 분석 캐시를 조합하여 **종목별 BUY/HOLD/SELL 안내 카드**를 생성하고, 전체 포트폴리오에 대해서는 **집중도 / 섹터 편중 / 데이터 부족 / 비용 사용 상태**를 요약한다.

본 기능은 투자 자문 확정이나 자동 매매가 아니라, 사용자가 직접 판단할 수 있도록 근거를 정리하는 **의사결정 지원 기능**이다.

---

## 3. 핵심 요약 표

| 항목 | 내용 |
|------|------|
| 기능명 | 포트폴리오 일괄 안내 기능 |
| 기능 ID | `F-BULK-01` |
| 목적 | 사용자가 보유 종목 전체에 대해 일괄 분석을 실행하고, 종목별 BUY/HOLD/SELL 안내와 포트폴리오 차원의 리스크 요약을 받도록 지원 |
| 주요 사용자 | 로그인한 개인 투자자, PM/시연 사용자 |
| 주 트리거 | `포트폴리오 일괄 안내 받기` 버튼 클릭 |
| 전제조건 | 로그인 완료, `holdings`에 1개 이상 보유 종목 존재, `company`/`stock_price` 기본 데이터 적재 |
| 주요 입력 | `user_id`, 보유 종목 목록, 평균 매수가, 수량, 분석 깊이, 비용 모드 |
| 메인 에이전트 | Strategist & Synthesizer Agent |
| 보조 에이전트 | Quant Worker, Qual Worker, Competitor Agent, Guardrail Agent |
| 주요 DB | `users`, `holdings`, `company`, `stock_price`, `financial_statement`, `financial_data`, `rag_documents`, `rag_chunks`, `analysis_cache`, `analysis_history`, `llm_cost_log` |
| 주요 출력 | 종목별 안내 카드, 포트폴리오 요약 카드, 리스크 경고, 근거 요약, `analysis_history` 저장 |
| LLM 비용 정책 | 월 LLM 비용 5만원 상한 준수, 종목 수/분석 깊이에 따라 캐시·요약·저비용 모델 우선 사용 |
| 대표 예외 | 보유 종목 없음, 시세 결손, DART/RAG 데이터 부족, LLM 실패, 월 비용 임계점 도달, 일부 종목 분석 실패 |
| MVP 범위 | 보유 종목을 순회해 종목별 간단 안내와 전체 포트폴리오 요약 제공. PB 리포트 PDF/DOCX 일괄 생성은 후속 범위 |
| 제외 범위 | 자동 매매, 투자 자문 확정 표현, 실시간 주문 연동, 보장 수익률 제시 |

---

## 4. F-BULK-01. 포트폴리오 일괄 안내 기능

### 4.1 트리거

- 사용자가 로그인 후 포트폴리오 화면에서 `포트폴리오 일괄 안내 받기` 버튼을 클릭한다.
- 사용자가 보유 종목 목록을 CSV로 업로드한 뒤 `전체 분석 시작` 버튼을 클릭한다.
- 향후 운영 모드에서는 매일 장 마감 이후 관심 사용자 또는 시연 계정에 대해 백그라운드 사전 분석이 실행될 수 있다.

### 4.2 전제조건

| 조건 | 상세 |
|------|------|
| 로그인 | `users` 테이블에 사용자 정보가 존재하고 세션에서 `user_id`를 확인할 수 있어야 한다. |
| 보유 종목 | `holdings` 테이블에 `user_id` 기준 1개 이상 보유 종목이 있어야 한다. |
| 종목 마스터 | `company` 테이블에 보유 종목의 `stock_code`, `corp_name`, `sector`가 있어야 한다. |
| 시세 데이터 | `stock_price` 또는 외부 시세 캐시에 최근 가격이 있어야 한다. |
| 비용 정책 | `llm_cost_log` 기준 월 누적 LLM 비용이 5만원 미만이어야 하며, 4만원 이상이면 캐시 모드를 우선 적용한다. |
| 캐시 테이블 | 24시간 내 분석 결과 조회를 위해 `analysis_cache` 또는 이에 준하는 캐시 저장소가 준비되어야 한다. |
| RAG 데이터 | 정성 분석을 사용하는 경우 `rag_documents`, `rag_chunks`에 뉴스/공시 청크가 적재되어 있어야 한다. |

### 4.3 입력

| 필드 | 타입 | 필수 | 출처 | 설명 |
|------|------|------|------|------|
| `user_id` | uuid | 필수 | 세션 | 현재 로그인 사용자 식별자 |
| `portfolio_id` | uuid/string | 선택 | UI/DB | 향후 다중 포트폴리오 지원 시 사용 |
| `stock_code` | string(6) | 필수 | `holdings` | 한국 상장 종목 코드 |
| `corp_name` | string | 선택 | `company` | UI 표시용 종목명 |
| `avg_price` | int/decimal | 필수 | `holdings` | 평균 매수가 |
| `qty` | int | 필수 | `holdings` | 보유 수량 |
| `bought_at` | date | 선택 | `holdings` | 최초 또는 대표 매수일 |
| `current_price` | int/decimal | 선택 | `stock_price` | 최근 종가 또는 현재가 |
| `sector` | string | 선택 | `company` | 섹터 편중 계산에 사용 |
| `analysis_depth` | enum | 선택 | UI | `summary`, `standard`, `deep` 중 하나. MVP 기본값은 `summary` |
| `cost_mode` | enum | 선택 | UI/운영 설정 | `cache_only`, `low_cost`, `standard` 중 하나. 비용 임계점 도달 시 강제 변경 가능 |
| `force_refresh` | boolean | 선택 | UI | 24시간 캐시를 무시하고 재분석할지 여부. 기본값 `false` |
| `max_symbols_per_batch` | int | 선택 | 시스템 설정 | 1회 처리 종목 수. 기본값 5 |

### 4.4 처리 흐름

1. **사용자 요청 수신**
   - UI는 `user_id`, `analysis_depth`, `cost_mode`, `force_refresh`를 포함해 일괄 안내 요청을 생성한다.
   - 버튼 클릭 직후 UI에는 `분석 요청을 접수했습니다` 상태를 표시하고, 종목 수가 10개 이상이면 즉시 백그라운드/순차 처리 모드로 전환한다.

2. **보유 종목 조회 및 기본 검증**
   - `holdings`에서 `user_id` 기준 보유 종목을 조회한다.
   - `company`를 조인하여 종목명, 섹터, 상장 상태를 확인한다.
   - `stock_price`를 조인하여 최근 가격을 가져온다.
   - 수량이 0 이하이거나 종목 코드가 없는 행은 분석 대상에서 제외하고, 제외 사유를 UI에 표시한다.

3. **포트폴리오 기본 수치 계산**
   - LLM 호출 없이 Python/SQL로 평가금액, 평가손익, 수익률, 종목별 비중, 섹터별 비중을 계산한다.
   - 이 단계는 항상 LLM보다 먼저 수행한다.
   - 계산 결과는 이후 Strategist Agent의 입력 컨텍스트로 사용한다.

4. **월 LLM 비용 상태 확인**
   - `llm_cost_log`에서 당월 누적 비용을 조회한다.
   - 누적 비용이 3만원 이상이면 UI에 비용 주의 상태를 표시한다.
   - 누적 비용이 4만원 이상이면 신규 LLM 분석을 제한하고 `cache_only` 또는 `low_cost` 모드로 강제 전환한다.
   - 누적 비용이 5만원 이상이면 신규 LLM 호출을 차단하고 캐시 결과와 정량 계산 결과만 제공한다.

5. **24시간 Postgres 캐시 우선 조회**
   - 각 `stock_code`에 대해 LLM 호출 전에 반드시 `analysis_cache` 또는 `analysis_history`에서 24시간 내 동일 사용자/동일 종목/동일 분석 깊이의 분석 결과를 조회한다.
   - 캐시 키는 최소한 `user_id`, `stock_code`, `analysis_depth`, `cache_version` 조합으로 구성한다.
   - `force_refresh=false`이고 24시간 내 캐시가 있으면 해당 종목은 LLM 호출 없이 캐시 결과를 반환한다.
   - 캐시 결과에는 `cached=true`, `cached_at`, `source_analysis_id`를 포함해 UI에서 재사용 결과임을 표시한다.
   - 이 캐시 조회는 Quant, Qual, Competitor, Strategist 호출보다 항상 먼저 실행한다.

6. **분석 대상 분리**
   - 24시간 캐시가 있는 종목은 `cached_symbols`로 분류한다.
   - 캐시가 없지만 정량 데이터만으로 안내 가능한 종목은 `quant_only_symbols`로 분류한다.
   - 캐시가 없고 데이터가 충분한 종목은 `live_analysis_symbols`로 분류한다.
   - 데이터가 부족한 종목은 `skipped_symbols`로 분류하고, 부족한 데이터 항목을 기록한다.

7. **대량 보유 종목 Batch 처리**
   - 보유 종목이 10개 미만이면 UI 세션 내에서 순차 처리하되, 종목별 진행률을 표시한다.
   - 보유 종목이 10개 이상이면 UI가 멈추지 않도록 백그라운드 작업 또는 Batch 큐 방식으로 처리한다.
   - 기본 Batch 크기는 5종목이며, 각 Batch 완료 시 UI에 부분 결과를 먼저 렌더링한다.
   - Streamlit MVP에서는 완전한 작업 큐가 없더라도 `st.session_state`에 작업 상태를 저장하고, `분석 계속 진행 중` 상태와 새로고침 가능한 부분 결과를 제공한다.
   - 향후 운영 버전에서는 Celery, RQ, APScheduler, 또는 별도 worker 프로세스로 분리한다.

8. **종목별 정량 분석**
   - Quant Worker가 `financial_statement` 또는 `financial_data`, `stock_price`, `holdings`를 사용해 수익률, 밸류에이션, 변동성, 비중을 계산한다.
   - PER, PBR, ROE, MoS, 평가손익 등 수식 계산은 LLM이 아니라 Python/SQL로 수행한다.
   - 재무 데이터가 부족하면 `quant_status=partial`로 표시하고 가능한 계산만 수행한다.

9. **종목별 정성/RAG 분석**
   - Qual Worker가 `rag_chunks`에서 최근 뉴스/공시 청크를 검색한다.
   - `analysis_depth=summary`인 경우 LLM 호출을 최소화하고 캐시된 요약 또는 상위 헤드라인 중심으로 처리한다.
   - `analysis_depth=standard` 이상에서만 호재/악재 자연어 요약 LLM 호출을 허용한다.
   - RAG 결과가 0건이면 정성 분석을 건너뛰고 `qual_status=no_data`로 표시한다.

10. **Peer/섹터 비교**
    - Competitor Agent가 `company.sector` 기준 Peer 후보를 찾는다.
    - MVP에서는 상세 Peer LLM 분석을 모든 종목에 실행하지 않고, 섹터 평균 또는 주요 지표 비교만 우선 제공한다.
    - 비용 여유가 있고 `analysis_depth=deep`인 경우에만 Peer 해석 LLM 호출을 허용한다.

11. **종목별 안내 합성**
    - Strategist & Synthesizer Agent가 Quant, Qual, Peer 결과를 종합해 종목별 `BUY`, `HOLD`, `SELL` 안내를 생성한다.
    - 캐시 종목은 기존 결과를 그대로 사용하되, 현재가와 수익률이 크게 달라진 경우 `가격 변동 후 재확인 필요` 경고를 붙인다.
    - 신규 LLM 호출이 필요한 경우에도 종목별 전체 상세 보고서가 아니라 4슬롯 요약인 `WHAT / HOW MUCH / WHY / RISK`만 생성한다.

12. **포트폴리오 레벨 종합**
    - 모든 종목 결과를 모아 포트폴리오 전체 판단을 생성한다.
    - LLM 호출 전 Python/SQL로 집중도, 섹터 편중, 손실 상위 종목, 수익 기여 상위 종목을 계산한다.
    - 비용 모드가 `low_cost`이면 포트폴리오 종합 문장은 템플릿 기반으로 생성하고 LLM 호출을 생략한다.
    - 비용 여유가 있으면 Strategist가 포트폴리오 요약 LLM 호출 1회를 수행한다.

13. **Guardrail 검증**
    - Guardrail Agent가 투자 자문 확정 표현, 보장 수익률, 과도한 매수/매도 단정, 출처 없는 주장, PII 노출을 검사한다.
    - 문제가 발견되면 문구를 완화하거나 해당 종목 카드에 `검증 필요` 상태를 표시한다.

14. **결과 저장**
    - 종목별 분석 결과는 `analysis_cache`에 저장하여 24시간 캐시로 재사용한다.
    - 사용자에게 노출된 최종 일괄 안내 결과는 `analysis_history`에 저장한다.
    - 모든 LLM 호출은 `llm_cost_log`에 모델, 토큰, 비용, 캐시 여부와 함께 기록한다.

15. **UI 렌더링**
    - 캐시 결과, 진행 중 결과, 실패 결과, 완료 결과를 구분해 표시한다.
    - 대량 종목 분석 중에는 전체 완료를 기다리지 않고 Batch별 부분 결과를 먼저 표시한다.
    - 최종 완료 시 `분석 완료`, `캐시 사용 종목 수`, `신규 분석 종목 수`, `실패/제외 종목 수`, `추정 LLM 비용`을 표시한다.

### 4.5 출력

| 출력 대상 | 필드/요소 | 타입 | 설명 |
|-----------|-----------|------|------|
| UI | 포트폴리오 요약 카드 | component | 총 평가금액, 총 손익, 평균 수익률, 현금 비중 |
| UI | 섹터 편중 카드 | component/chart | 섹터별 비중과 편중 경고 |
| UI | 종목별 안내 카드 | component list | 종목명, 현재가, 수익률, BUY/HOLD/SELL, 신뢰도, 주요 근거 |
| UI | 캐시 표시 | badge | `24시간 내 분석 재사용`, `신규 분석`, `부분 분석` 상태 |
| UI | 진행률 | progress/status | Batch 처리 진행률, 완료/실패 종목 수 |
| UI | 리스크 경고 | alert | 비용 임계점, 데이터 부족, 과도한 집중도, 분석 실패 |
| UI | 면책 문구 | text | 투자 판단은 사용자 책임이며 시스템 출력은 참고 정보임을 고지 |
| DB | `analysis_cache` | row/json | 종목별 24시간 재사용 가능한 분석 결과 |
| DB | `analysis_history` | row/json | 사용자에게 실제 노출한 일괄 안내 결과 |
| DB | `llm_cost_log` | row | LLM 호출 비용, 모델, 토큰, 캐시 여부 |
| LangGraph State | `BulkPortfolioAdvice` | object | 전체 일괄 분석 상태와 종목별 결과 |

`BulkPortfolioAdvice` 예상 구조:

| 필드 | 타입 | 설명 |
|------|------|------|
| `user_id` | uuid | 사용자 ID |
| `requested_at` | datetime | 요청 시각 |
| `portfolio_summary` | object | 포트폴리오 총괄 수치 |
| `symbol_results` | list | 종목별 분석 결과 |
| `cached_count` | int | 캐시 사용 종목 수 |
| `live_analysis_count` | int | 신규 분석 종목 수 |
| `failed_count` | int | 실패 또는 제외 종목 수 |
| `estimated_cost_krw` | decimal | 이번 요청의 추정 LLM 비용 |
| `cost_mode` | enum | 적용된 비용 모드 |
| `status` | enum | `queued`, `running`, `partial`, `completed`, `failed` |

### 4.6 예외 처리

| 예외 상황 | 감지 조건 | 처리 방안 | 사용자 메시지 |
|-----------|-----------|-----------|---------------|
| 보유 종목 없음 | `holdings` 조회 결과 0건 | 분석 실행 중단, 보유 종목 등록 화면으로 안내 | `보유 종목을 먼저 추가해 주세요.` |
| 잘못된 종목 코드 | `company` 조인 실패 | 해당 종목 제외, 나머지 종목 계속 분석 | `일부 종목은 종목 마스터에서 확인되지 않아 제외했습니다.` |
| 시세 데이터 결손 | `stock_price` 최근 가격 없음 | 평가금액 계산에서 제외하거나 직전 유효 가격 사용, 경고 표시 | `일부 종목의 최신 시세가 없어 직전 데이터로 계산했습니다.` |
| 재무 데이터 부족 | `financial_statement`/`financial_data` 부족 | Quant 결과를 `partial`로 표시, 정성/캐시 결과 중심으로 안내 | `재무 데이터가 부족해 일부 지표는 생략되었습니다.` |
| RAG 데이터 없음 | `rag_chunks` 검색 결과 0건 | Qual 분석 생략, 뉴스/공시 근거 없음 표시 | `최근 뉴스/공시 데이터가 부족합니다.` |
| 24시간 캐시 존재 | `analysis_cache.created_at >= now() - 24h` | LLM 호출 없이 캐시 반환 | `24시간 내 분석 결과를 재사용했습니다.` |
| 캐시 만료 | 24시간 초과 | 비용 상태 확인 후 신규 분석 또는 정량-only 분석 | `기존 분석이 오래되어 새로 확인합니다.` |
| 보유 종목 10개 이상 | `holdings_count >= 10` | 백그라운드 또는 Batch 처리로 전환, 부분 결과 표시 | `보유 종목이 많아 순차 분석으로 진행합니다. 완료된 결과부터 보여드립니다.` |
| API 타임아웃 | 외부 API 또는 LLM 30초 초과 | 1회 재시도, 실패 시 해당 종목만 부분 실패 처리 | `일부 종목 분석이 지연되어 가능한 결과부터 표시합니다.` |
| LLM 호출 실패 | provider error, timeout, schema violation | Solar -> gpt-4o-mini fallback, 1회 재시도 후 캐시/정량 결과로 대체 | `AI 요약 생성에 실패해 계산 결과 중심으로 표시합니다.` |
| LLM 응답 스키마 위반 | Pydantic 검증 실패 | 1회 재시도, 실패 시 해당 필드 비움 및 Guardrail 경고 | `일부 설명 문구를 생성하지 못했습니다.` |
| 월 비용 3만원 도달 | `sum(cost_krw) >= 30000` | UI/관리자 경고, 저비용 모델 우선 | `이번 달 AI 사용량이 높아지고 있습니다.` |
| 월 비용 4만원 도달 | `sum(cost_krw) >= 40000` | 신규 상세 분석 제한, 캐시 모드 강제 | `비용 보호를 위해 최근 분석 결과와 기본 지표 중심으로 안내합니다.` |
| 월 비용 5만원 도달 | `sum(cost_krw) >= 50000` | 신규 LLM 호출 차단, 캐시/정량-only 출력 | `월 비용 상한에 도달해 신규 AI 분석은 일시 중단됩니다.` |
| 일부 종목 실패 | Batch 내 일부 실패 | 실패 종목만 `failed` 표시, 전체 요청은 `partial`로 완료 | `일부 종목은 분석하지 못했지만 나머지 결과는 확인할 수 있습니다.` |
| UI 세션 끊김 | Streamlit 세션 리셋 | `analysis_history` 또는 작업 상태에서 복구 | `이전 분석 상태를 불러왔습니다.` |

대량 종목 처리 UX 기준:

| 종목 수 | 처리 방식 | UI 정책 | LLM 정책 |
|---------|-----------|---------|----------|
| 1~4개 | 즉시 순차 처리 | 단일 진행률 표시 | 캐시 우선, 필요 시 종목별 최소 호출 |
| 5~9개 | 소규모 Batch | 종목별 완료 카드 즉시 표시 | 캐시 우선, 상세 분석은 비용 상태에 따라 제한 |
| 10개 이상 | 백그라운드/순차 Batch | UI 멈춤 방지, 완료된 Batch부터 렌더링 | `summary` 기본, 캐시/정량-only 우선 |
| 20개 이상 | 강제 요약 모드 | 전체 상세 분석 대신 상위 리스크/비중 종목 우선 | 신규 LLM 호출은 포트폴리오 요약 1회 이내 권장 |

비용 보호 기준:

| 비용 상태 | 기준 | 동작 |
|-----------|------|------|
| 정상 | 월 누적 3만원 미만 | 캐시 우선 후 필요한 신규 분석 허용 |
| 주의 | 월 누적 3만원 이상 | 저비용 모델 우선, UI에 주의 표시 |
| 제한 | 월 누적 4만원 이상 | `cache_only` 또는 `low_cost` 강제, 신규 상세 LLM 제한 |
| 차단 | 월 누적 5만원 이상 | 신규 LLM 호출 차단, 캐시/정량 계산만 제공 |

### 4.7 담당

| 영역 | 메인 담당 | 보조 담당 | 관련 파일/테이블 |
|------|-----------|-----------|------------------|
| UI 요청/진행률 | Streamlit UI | PM | `streamlit_app.py`, `pages/`, `ui/components/` |
| 보유 종목 조회 | Backend/DB | Quant Worker | `holdings`, `company`, `stock_price` |
| 24시간 캐시 조회 | Backend/LLM layer | Strategist | `analysis_cache`, `analysis_history` |
| 정량 계산 | Quant Worker | Backend | `financial_statement`, `financial_data`, `stock_price`, `holdings` |
| 정성/RAG 요약 | Qual Worker | Guardrail | `rag_documents`, `rag_chunks`, `disclosure` |
| Peer 비교 | Competitor Agent | Quant Worker | `company`, `financial_data`, `stock_price` |
| 종목별 안내 합성 | Strategist & Synthesizer Agent | Quant, Qual, Competitor | LangGraph State |
| 안전성 검증 | Guardrail Agent | PM | 출력 필터, 면책 문구 |
| 비용 추적 | LLM layer | PM | `llm_cost_log`, `docs/operations/llm_cost_guide.md` |
| 결과 저장 | Backend/DB | Strategist | `analysis_cache`, `analysis_history` |

---

## 5. 기능-에이전트-DB-LLM 호출 매핑

| 단계 | 메인 에이전트 | 보조 에이전트 | 사용 DB | LLM 호출 |
|------|---------------|---------------|---------|----------|
| 보유 종목 조회 | 없음 | 없음 | `holdings`, `company` | 0 |
| 포트폴리오 수치 계산 | Quant Worker | 없음 | `holdings`, `stock_price` | 0 |
| 24시간 캐시 조회 | 없음 | 없음 | `analysis_cache`, `analysis_history` | 0 |
| 정량 분석 | Quant Worker | 없음 | `financial_statement`, `financial_data`, `stock_price` | 0~1 |
| 정성 분석 | Qual Worker | Guardrail | `rag_documents`, `rag_chunks`, `disclosure` | 0~1 per uncached symbol, summary 모드에서는 생략 가능 |
| Peer 비교 | Competitor Agent | Quant Worker | `company`, `financial_data`, `stock_price` | 0~1, deep 모드에서만 권장 |
| 종목별 안내 합성 | Strategist | Quant, Qual, Competitor | LangGraph State | 0~1 per uncached symbol |
| 포트폴리오 종합 | Strategist | Guardrail | `analysis_history` | 0~1 per request |
| 안전성 검증 | Guardrail | 없음 | 없음 | 0~1, 규칙 기반 우선 |
| 비용 기록 | 없음 | 없음 | `llm_cost_log` | 0 |

MVP 권장 호출량:

| 상황 | 권장 LLM 호출 |
|------|---------------|
| 모든 종목 24시간 캐시 존재 | 0회 |
| 5종목 이하, 캐시 없음, summary | 포트폴리오 요약 1회 + 필요한 종목만 1회 |
| 10종목 이상, 캐시 일부 존재 | 신규 분석 종목에 한해 Batch별 최소 호출, 포트폴리오 요약 1회 이내 |
| 월 비용 4만원 이상 | 신규 상세 호출 금지, 캐시/정량-only |
| 월 비용 5만원 이상 | 신규 LLM 호출 0회 |

---

## 6. KPI / 비용 상한 / 운영 기준

| 구분 | 지표 | 목표/임계값 | 비고 |
|------|------|-------------|------|
| 비용 | 월 LLM 비용 | 5만원 이하 | PRD Non-goal 및 ADR 비용 정책 준수 |
| 비용 | 캐시 적중률 | 50% 이상 목표 | 시연/반복 분석에서는 80% 이상 권장 |
| 성능 | 5종목 이하 응답 시간 | 30초 이내 목표 | 캐시 적중 시 5초 이내 |
| 성능 | 10종목 이상 UX | UI 멈춤 없음 | Batch/부분 결과 렌더링 필수 |
| 안정성 | 일부 실패 허용 | 전체 실패 대신 `partial` 완료 | 실패 종목과 사유 표시 |
| 품질 | 출처 포함률 | 정성 근거 95% 이상 | RAG 사용 시 URL/문서명/일자 포함 |
| 안전성 | 투자 확정 표현 차단 | 100% | Guardrail 필수 |
| 저장 | 분석 이력 저장 | 요청 단위 1건 이상 | `analysis_history` 기준 |

운영 정책:

- 기본 분석 깊이는 `summary`로 시작한다.
- 사용자가 상세 분석을 원할 경우에도 24시간 캐시를 먼저 조회한다.
- 계산 가능한 수치 분석은 LLM 없이 Python/SQL로 처리한다.
- 신규 LLM 호출은 반드시 비용 라우팅 계층을 거쳐야 한다.
- 월 비용 4만원 이상부터는 PM 승인 없이 신규 상세 분석을 확장하지 않는다.
- 월 비용 5만원 도달 시 신규 LLM 호출을 차단하고 캐시/정량 결과만 제공한다.

---

## 7. 변경 이력

| 날짜 | 버전 | 변경 |
|------|------|------|
| 2026-05-23 | v0.2 | 포트폴리오 일괄 안내 기능 초안 작성. 24시간 Postgres 캐시 우선 조회, 10개 이상 보유 종목 Batch 처리, 월 LLM 비용 5만원 상한, 예외 처리 기준 반영 |
