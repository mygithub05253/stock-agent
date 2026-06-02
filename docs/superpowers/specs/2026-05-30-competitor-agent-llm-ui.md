# Competitor Agent — LLM 서술 레이어 + UI 강화 설계서

| 항목 | 값 |
|------|-----|
| 작성일 | 2026-05-30 |
| 상태 | 사용자 검토 대기 |
| 선행 문서 | `docs/superpowers/specs/2026-05-26-competitor-agent-design.md` (Rule-based 코어 완료) |
| 관련 명세 | `docs/functional-spec/advanced/A3_peer_comparison_spec_v0.9.md` |
| 주요 독자 | Competitor Agent 담당자, PM, UI 담당 팀원 |

---

## 1. 맥락 — 이미 구현된 것과 이번에 추가할 것

### 이미 완료된 상태
- `tools/peer_tool.py` — DB 조회, PER/PBR/ROE/성장률/마진/부채비율 계산, 백분위 점수, `build_peer_comparison` 빌더 구현 완료
- `agents/competitor.py` — DB 연결 → `peer_tool` 호출 → `CompetitorResult` 반환, DB 실패 시 mock fallback 구현 완료
- `schemas/analysis.py` — `CompetitorResult` 확장 필드 완료
- `prompts/competitor/system.md` — 프롬프트 파일 존재하나 코드에서 호출되지 않음

### 이번 범위에서 추가할 것

| 추가 항목 | 이유 |
|-----------|------|
| OpenRouter 클라이언트 | GLM-free와 유사한 비용 (~₩0.3/call), 유연한 모델 교체 |
| 시가총액 밴드 필터 (0.25x~4x) | A3 명세 `same_sector_marketcap_near` 요건, 이질적 peer 제거 |
| 인메모리 24h 캐시 | A3 명세 요건, 동일 종목 반복 호출 시 LLM 0회 |
| LLM 서술 레이어 | rule-based 수치 → GLM/OpenRouter → 고품질 narrative 생성 |
| 이상치(outlier) 처리 | A3 명세 Winsorize 요건, peer 중앙값 10배 초과 지표 플래그 |
| `competitor/system.md` 프롬프트 전면 개선 | GIC v11 Block G(Evidence Card) + F(Red Team) + J(Anti-Hallucination) 적용 |
| Streamlit UI — peer 메트릭 테이블 + evidence 카드 | 사용자가 숫자를 직접 확인할 수 있는 최소 UI |

---

## 2. 아키텍처 — 3-Phase 내부 구조

`run_competitor`의 외부 인터페이스(`AgentState` 입출력)는 변경하지 않는다.
다른 팀원 코드(Strategist, pipeline.py, streamlit_app.py)와의 충돌이 없다.

```
run_competitor(state: AgentState) → AgentState
│
├── Phase 1 — Peer 데이터 수집 및 계산 (₩0, rule-based, 기존 유지 + 밴드 필터 추가)
│   ├── DB: load_target_company + load_peer_candidates (기존)
│   ├── 신규: market_cap 밴드 필터 0.25x~4x (same_sector_marketcap_near)
│   ├── 신규: outlier Winsorize — peer 중앙값 10배 초과 지표 → low_similarity 플래그
│   └── PER/PBR/ROE/성장률/마진/부채비율 계산 + 백분위 점수 (기존 유지)
│
├── Phase 2 — 24h 캐시 확인 (₩0)
│   ├── 키: {stock_code}_{YYYY-MM-DD}
│   ├── 캐시 HIT → Phase 3 건너뜀, 캐시된 narrative 재사용
│   └── 캐시 MISS → Phase 3 진행
│
└── Phase 3 — LLM 서술 생성 (OpenRouter, 캐시 미스 시에만)
    ├── 입력: PeerComparison JSON (수치만, LLM이 숫자를 만들지 않음)
    ├── OpenRouter `google/gemini-flash-1.5` 호출 (config에서 override 가능)
    ├── 출력 JSON: peer_summary + evidence_cards + bear_case + data_gaps
    ├── 24h 캐시에 결과 저장
    ├── CompetitorResult 필드에 merge (수치는 rule-based 그대로, 서술만 LLM)
    └── 실패 / 타임아웃 → rule-based build_peer_summary() 문자열로 graceful fallback
```

---

## 3. 신규 파일 및 변경 파일

| 파일 | 작업 | 핵심 내용 |
|------|------|-----------|
| `src/stock_agent/llm/openrouter_client.py` | 신규 생성 | glm_client.py 패턴 동일. base_url=openrouter.ai/api/v1, JSON 파싱 |
| `src/stock_agent/config.py` | 수정 | `openrouter_api_key`, `openrouter_model` 필드 추가 |
| `.env.example` | 수정 | `OPENROUTER_API_KEY=`, `OPENROUTER_MODEL=google/gemini-flash-1.5` 추가 |
| `src/stock_agent/tools/peer_tool.py` | 수정 | 시가총액 밴드 필터, outlier Winsorize 추가 |
| `src/stock_agent/agents/competitor.py` | 수정 | Phase 2 캐시 + Phase 3 LLM 호출 추가 |
| `src/stock_agent/prompts/competitor/system.md` | 전면 재작성 | GIC v11 Block G/F/J 패턴 적용, JSON 출력 스키마 명시 |
| `streamlit_app.py` 또는 관련 UI 파일 | 수정 | peer 메트릭 테이블(st.dataframe) + evidence 카드 + bear_case 박스 |
| `tests/llm/test_openrouter_client.py` | 신규 생성 | JSON 파싱, fence 제거, 실패 시 예외 검증 |
| `tests/agents/test_competitor_llm.py` | 신규 생성 | LLM 호출 monkeypatch, 캐시 hit/miss, fallback 검증 |

---

## 4. OpenRouter 클라이언트 설계

`glm_client.py`와 거의 동일한 구조. 재사용 가능하도록 유사하게 설계.

```python
# src/stock_agent/llm/openrouter_client.py
# base_url  : https://openrouter.ai/api/v1/chat/completions
# model     : config.openrouter_model (기본: google/gemini-flash-1.5)
# max_tokens: 800
# temperature: 0.2
# 출력      : JSON dict (glm_client._strip_json_fence 로직 동일)
# 실패 시   : OpenRouterClientError 발생
```

---

## 5. 인메모리 캐시 설계

```python
# competitor.py 모듈 레벨
_narrative_cache: dict[str, dict] = {}
# 키: "{stock_code}_{date.today().isoformat()}"
# 값: LLM 반환 narrative dict
# TTL: 날짜 기반 (다음 날 자동 만료)
# 용도: 동일 종목 동일 날짜 반복 호출 시 LLM 호출 0회
```

Streamlit 재시작 시 캐시 초기화됨 → 간단하고 충분함. DB `analysis_cache` 연동은 향후 PR로 분리.

---

## 6. LLM 출력 JSON 스키마

LLM이 반환해야 하는 JSON 구조. 수치는 입력 데이터에서만 인용 (Block J).

```json
{
  "peer_summary": "2~3문장. 밸류에이션 위치 + 핵심 강점/약점 서술.",
  "evidence_cards": [
    {
      "finding": "한 줄 핵심 발견",
      "metric_basis": "PER 18.4x vs peer 중위 15.2x 등 수치 근거",
      "confidence": "high | medium | low",
      "flag": "strength | risk | neutral"
    }
  ],
  "bear_case": "Short-seller 관점 1~2문장. peer 대비 약점 + 전제 조건 위협.",
  "data_gaps": ["결측 지표 명시 리스트"]
}
```

파싱 실패 또는 필수 필드 누락 시 → rule-based 문자열 fallback으로 대체.

---

## 7. `competitor/system.md` 핵심 구조 (GIC v11 벤치마킹)

GIC v11에서 벤치마킹할 항목 (그대로 복사하지 않고 DB 기반 구조화 출력에 맞게 커스터마이징):

| GIC v11 블록 | 적용 방식 |
|--------------|-----------|
| Block J (Anti-Hallucination) | 수치를 임의 생성 금지, 결측 데이터는 `data_gaps`에 명시 |
| Block G (Evidence Card) | `evidence_cards` 배열로 finding + metric_basis + confidence + flag 출력 |
| Block F (Red Team) | `bear_case` 필드로 short-seller 관점 1~2문장 의무화 |
| Block B (Sanity Check) | 단일 지표 단정 금지 (낮은 PER = 자동 저평가 금지) |

---

## 8. 시가총액 밴드 필터 (peer_tool.py 수정)

A3 명세의 `same_sector_marketcap_near` 모드를 기본 적용.

```python
# load_peer_candidates 수정
# target.market_cap 이 있을 때: 후보 중 market_cap이 0.25x~4x 범위인 기업 우선
# target.market_cap 이 없을 때: 기존 sector 기반 정렬 유지 (호환성)
MARKET_CAP_BAND_LOW  = 0.25
MARKET_CAP_BAND_HIGH = 4.0
```

---

## 9. Outlier Winsorize (peer_tool.py 수정)

A3 명세 요건: peer 중앙값의 10배 초과 지표는 `low_similarity` 플래그.

```python
# select_peer_rows 또는 calculate_relative_position 내부에서 적용
# 지표값이 peer 중앙값의 10배 초과 → row.metric_flags에 "outlier_{metric}" 추가
# 이 row는 해당 지표 백분위 계산에서 제외, PeerComparison.warnings에 반영
```

---

## 10. UI 변경 (Streamlit)

기존 Tier 2 카드의 `Peer 비교` 섹션에 추가. 기존 컴포넌트 최대 재활용.

### 10.1 Peer 메트릭 테이블
```python
# st.dataframe() 로 종목명/PER/PBR/ROE/영업이익률/매출성장률 5열 표시
# 대상 종목은 첫 행 강조
# 결측값은 "N/A" 표시
```

### 10.2 Evidence 카드 (LLM 있을 때)
```
🟢 [high] finding 문장 (metric_basis)
🟡 [medium] ...
🔴 [low] ...
```

### 10.3 Bear Case 박스 (LLM 있을 때)
```python
st.warning("⚠️ 리스크 관점: " + bear_case)
```

### 10.4 Mock fallback / LLM 없을 때
기존 evidence 리스트 그대로 유지. UI 하위 호환성 완전 보장.

---

## 11. 예외 처리 및 fallback 체인

```
DB 연결 성공
  → peer_tool 계산 → 캐시 확인 → LLM 호출
    → LLM 성공: LLM narrative merge
    → LLM 실패 / 타임아웃: rule-based 문자열 사용
DB 연결 실패
  → mock fallback (기존 그대로, mock_data_fallback 경고)
OpenRouter key 없음
  → LLM 호출 건너뜀, rule-based 문자열 사용
```

---

## 12. 브랜치 및 협업 가이드 준수

```
브랜치명: feature/competitor-llm-ui
베이스  : main (최신 pull 후 작업)
PR 대상 : dev
```

작업 전 `git pull origin main` 필수. 다른 팀원이 수정할 가능성 있는 파일:
- `streamlit_app.py` — UI 팀 수정 가능. 충돌 시 peer 섹션만 추가하는 방식으로 최소화.
- `schemas/analysis.py` — 필드 추가만. 기존 필드 삭제/변경 금지.
- `config.py` — 필드 추가만.

---

## 13. 비용 정책

| 모델 | 호출당 비용 | 24h 캐시 적용 시 |
|------|------------|-----------------|
| `google/gemini-flash-1.5` (OpenRouter) | ~₩0.3 | 종목당 하루 1회만 |
| `meta-llama/llama-3.1-8b-instruct` (OpenRouter free tier) | ₩0 | - |

A3 명세의 월 ₩50,000 상한 내에서 여유 있음. OpenRouter key 없거나 실패 시 ₩0.

---

## 14. 자체 검토

- **미완성 표식**: 없음.
- **A3 명세 대응**: 시가총액 밴드, Winsorize, 24h 캐시, LLM 2회 상한(이번은 1회), 비용 임계점 fallback 모두 반영.
- **기존 코드 호환성**: `CompetitorResult` 필드 추가 없음. `AgentState` 계약 변경 없음. 기존 테스트 회귀 없음.
- **범위 제한**: 글로벌 peer, DB `analysis_cache` 영구 저장, A1 상대가치 연계 자동화는 이번 PR 범위 밖.
- **팀 일관성**: `glm_client.py` 패턴 재활용, `investment_analyst.py` LLM 레이어 패턴 동일 적용.
