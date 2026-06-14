# Macro Agent — 거시경제 맥락 분석

## 개요

Macro Agent는 한국은행 ECOS API로 수집한 거시경제 지표를 분석해 투자 환경의 거시적 맥락을 평가합니다.
Quant·Qual·Competitor의 **미시 분석**을 보완하는 **하향식(Top-Down) 분석** 레이어입니다.

### 이론적 근거

| 논문 | 핵심 내용 | 적용 |
|------|-----------|------|
| Miyazaki et al. (2026). *Toward Expert Investment Teams: A Multi-Agent LLM System with Fine-Grained Trading Tasks.* arXiv:2602.23330 | 금리/인플레이션/경제성장/시장 4개 영역을 0~100점으로 평가 + 현재값(Level)과 변화율(RoC) 동시 분석 | 점수 계산 구조, RoC 로직 |
| Yang et al. (2018). *Macroeconomic shocks and stock market returns: the case of Korea.* Applied Economics, 50(7) | 금리↑ = 주가↓, 수요 충격 = 주가↑, 환율과 금리를 포함한 5변수 구조 | 금리/환율 점수 로직 |
| PLOS ONE (2024). *Heterogeneous macroeconomic factors' effects on stocks across sizes, styles, and sectors in the South Korean market.* | 거시경제 변수가 11개 섹터에 각각 다르게 영향 — 환율↑ 시 외국인 매도, PPI↑ 시 변동성 확대 | 섹터별 가중치 차별화 |

---

## 파일 위치

```
src/stock_agent/agents/macro.py          ← 에이전트 구현
src/stock_agent/tools/macro_tool.py      ← DB 조회 Tool (별도 구현 완료)
src/stock_agent/prompts/macro/system.md  ← LLM 프롬프트 (향후 추가 예정)
tests/agents/test_macro_agent.py         ← 단위 테스트
```

---

## 입출력 인터페이스

### Input — `AgentState`

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `state.curator` | `CuratorResult` | ✅ | `sector` 필드 필요 (업종별 가중치 적용) |
| `state.as_of_date` | `str \| None` | ❌ | 백테스트 기준일. 없으면 오늘 날짜 사용 |

### Output — `MacroResult` (schemas/analysis.py에 추가 완료)

```python
class MacroResult(BaseModel):
    score: int = Field(ge=0, le=100)       # 거시경제 종합 점수
    macro_signal: Signal                    # BUY / HOLD / SELL
    indicators: dict[str, float | None]    # 사용된 지표값
    rate_of_change: dict[str, float | None] # 지표 변화율 (RoC)
    reasons: list[str]                      # 긍정 근거
    risks: list[str]                        # 리스크 근거
    sector: str                             # 적용된 업종
    as_of_date: str                         # 분석 기준일
```

---

## 점수 계산 로직

### 기본 구조 (Miyazaki et al. 2026 참고)

```
기본 50점에서 시작
    ↓
4개 영역 평가 → 가감점
    ↓
섹터별 가중치 적용
    ↓
RoC(변화율) 추가 보정
    ↓
최종 점수 → signal 결정
```

### 4개 영역 평가

| 영역 | 지표 | 긍정 조건 | 부정 조건 |
|------|------|-----------|-----------|
| **금리** | 기준금리, 국고채3년 | 금리 ≤ 2.5% → +15 | 금리 ≥ 3.5% → -15 |
| **인플레이션** | CPI, 생산자물가 | CPI ≤ 2.0% → +10 | CPI ≥ 4.0% → -15 |
| **경제성장** | GDP성장률, 산업생산 | GDP ≥ 2.0% → +10 | GDP ≤ 0% → -20 |
| **시장** | 코스피, 뉴스심리지수 | 심리지수 ≥ 110 → +5 | 심리지수 ≤ 90 → -5 |

> ⚠️ **[Phase 1 한계]** 현재 절대값 Threshold 기반 Rule-based 하드코딩입니다.
> 경제 상황에 따라 동일한 금리 수치가 다른 충격을 줄 수 있습니다.
> Phase 2에서 Z-Score(최근 3년 시계열 기준) 방식으로 개선 예정입니다.

### 섹터별 가중치 (PLOS ONE 2024 참고)

| 업종 | 환율 영향 | 금리 영향 |
|------|-----------|-----------|
| 반도체IT | 원화약세 → 수출유리 (+10) | 성장주 할인율 (-10) |
| 금융 | 수입비용 (-5) | 예대마진 확대 (+15) |
| 건설부동산 | 외자조달 불리 (-3) | 대출수요 급감 (-20) |
| 자동차제조 | 수출유리 (+8) | 할부수요 감소 (-8) |
| 에너지화학 | 일부유리 (+5) | 설비투자 위축 (-8) |

### 변화율(RoC) 보정 (Miyazaki et al. 2026 참고)

현재값뿐 아니라 **추세**도 함께 반영합니다.

```
금리가 높아도(3.5%) 하락 추세(-10%)면 → +5 추가 가점
CPI가 낮아도(2.0%) 상승 추세(+5%)면  → -3 추가 감점
```

#### 지표별 RoC 처리 방식

| 지표 | 처리 방식 | 이유 |
|------|-----------|------|
| 기준금리 | max_days=200 | 통방위 간격 최대 6개월 |
| CPI | max_days=45 | 월별 발표 |
| GDP | RoC 생략 | 이미 전년동기비 값 (2중 계산 방지) |

> ⚠️ **[Phase 1 한계]** 현재 지표별 발표 주기 불일치 문제가 있습니다.
> 날짜 간격 Guard Clause로 최소 방어하고 있으나,
> Phase 2에서 Window Function 단일 쿼리 + YoY/QoQ 별도 처리로 개선 예정입니다.

### Signal 결정 기준

```
score ≥ 70  →  BUY   (거시경제 우호적)
score ≥ 40  →  HOLD  (거시경제 중립)
score < 40  →  SELL  (거시경제 비우호적)
```

---

## 에이전트 책임 경계

| 해야 하는 일 | 하지 않는 일 |
|-------------|-------------|
| raw_macro 테이블에서 지표 조회 (macro_tool 경유) | DB 직접 접근 (반드시 macro_tool 사용) |
| 업종별 거시경제 점수 산출 | 개별 종목 재무 분석 (Quant 담당) |
| 금리/환율/물가/성장 추세 판단 | LLM으로 숫자 생성 |
| 거시 리스크 경고 문장 생성 | 최종 BUY/SELL 확정 (Strategist 담당) |
| DB 실패 시 mock fallback 반환 | |

---

## DB 연결 실패 시 Fallback

```python
_MACRO_FALLBACK = {
    "기준금리": 3.5,
    "원달러환율": 1380.0,
    "CPI": 2.3,
    "GDP성장률": 1.8,
    "코스피": 2550.0,
}
```

---

## 파이프라인 위치

```
Curator → RequestClassifier → Quant → Qual → Competitor
                                                    ↓
                                               [Macro]  ← 여기
                                                    ↓
                                              Strategist → Guardrail
```

---

## Phase 2 개선 계획

### 1. Z-Score 기반 점수 계산

```python
# 현재 (Phase 1)
if 금리 >= 3.5:
    score -= 15

# 개선 (Phase 2)
z = (현재금리 - 최근3년평균) / 최근3년표준편차
if z > 1.0: score -= 15
```

필요 작업: `get_macro_history()` 함수 추가 (macro_tool.py)

### 2. Window Function 단일 쿼리

```sql
-- 현재: 지표별 loop 쿼리 (N번 DB 접근)
-- 개선: 단일 쿼리로 최신 2개 레코드 조회
WITH RankedMacro AS (
    SELECT indicator_code, observed_at, payload,
           ROW_NUMBER() OVER (
               PARTITION BY indicator_code
               ORDER BY observed_at DESC
           ) as rn
    FROM raw_macro
    WHERE observed_at <= %s
      AND indicator_code IN (...)
)
SELECT * FROM RankedMacro WHERE rn <= 2;
```

---

## 테스트

```bash
pytest tests/agents/test_macro_agent.py -v
```

| 테스트 | 확인 내용 |
|--------|-----------|
| `test_run_macro_db_success` | DB 연결 성공 시 MacroResult 저장 확인 |
| `test_run_macro_db_failure_fallback` | DB 실패 시 mock fallback 동작 |
| `test_run_macro_no_curator` | Curator 없으면 ValueError 발생 |
| `test_run_macro_sector_difference` | 섹터별 점수 차이 검증 |
| `test_run_macro_roc_no_data` | RoC 데이터 부족 시 graceful 처리 |

---

## 작업 규칙 준수 사항

- ✅ **프롬프트 분리:** LLM 프롬프트는 `prompts/macro/system.md`에 별도 관리
- ✅ **Pydantic 스키마:** `MacroResult` 스키마를 `schemas/analysis.py`에 정의
- ✅ **Tool 분리:** DB 조회는 `macro_tool.py`에서만 처리
- ✅ **담당 1명 원칙:** melinamuun 단독 담당
- ✅ **테스트 파일:** `tests/agents/test_macro_agent.py` 작성 완료
- ✅ **출처 명시:** 점수 로직은 논문 근거 기반