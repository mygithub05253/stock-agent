# Competitor Agent LLM 서술 레이어 + UI 강화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** rule-based peer_tool 계산 결과 위에 OpenRouter LLM 서술 레이어(24h 캐시)를 추가하고, Streamlit Peer 탭에 peer 메트릭 테이블·evidence 카드·bear_case 박스를 렌더링한다.

**Architecture:** `competitor.py` 내부를 3-Phase로 구조화한다. Phase 1은 기존 rule-based `peer_tool.py`(수정 포함), Phase 2는 인메모리 24h 캐시 체크, Phase 3는 OpenRouter LLM 호출. `AgentState`·`CompetitorResult` 기존 필드는 변경하지 않고 `evidence_cards`, `bear_case` 두 필드만 추가한다. `glm_client.py`와 동일한 패턴으로 `openrouter_client.py`를 구현한다.

**Tech Stack:** Python 3.11, Pydantic v2, requests, psycopg v3, Streamlit, pytest, OpenRouter API (`google/gemini-flash-1.5`)

---

## 파일 구조

| 파일 | 작업 | 책임 |
|------|------|------|
| `src/stock_agent/config.py` | 수정 | `openrouter_api_key`, `openrouter_model`, `openrouter_base_url`, `openrouter_timeout_seconds` 추가 |
| `.env.example` | 수정 | `OPENROUTER_API_KEY=`, `OPENROUTER_MODEL=google/gemini-flash-1.5` 추가 |
| `src/stock_agent/llm/openrouter_client.py` | 신규 | OpenRouter chat completions 호출, JSON 파싱, `glm_client.py`와 동일 패턴 |
| `src/stock_agent/schemas/analysis.py` | 수정 | `CompetitorResult`에 `evidence_cards`, `bear_case` 추가 (기존 필드 변경 금지) |
| `src/stock_agent/tools/peer_tool.py` | 수정 | `select_peer_rows`에 market cap 밴드 필터(0.25x~4x) + `_mark_outliers` 추가 |
| `src/stock_agent/prompts/competitor/system.md` | 전면 재작성 | GIC v11 Block J/G/F/B 패턴, JSON 출력 스키마 명시 |
| `src/stock_agent/agents/competitor.py` | 수정 | 인메모리 캐시, `_generate_narrative`, `_apply_narrative`, Phase 3 연결 |
| `streamlit_app.py` | 수정 | `_render_peer_tab` 함수 추가, Peer 탭에서 호출 |
| `docs/agents/competitor_agent_flow.html` | 신규 | 3-Phase 흐름 시각화, 팀 수정 안내 |
| `tests/llm/__init__.py` | 신규 | 테스트 패키지 |
| `tests/llm/test_openrouter_client.py` | 신규 | JSON 파싱, fence 제거, HTTP 오류, key 없음 |
| `tests/agents/test_competitor_llm.py` | 신규 | 캐시 hit/miss, LLM fallback, narrative apply |

---

## Task 0: 브랜치 생성

- [ ] **Step 1: main 최신화 후 브랜치 생성**

```bash
git pull origin main
git checkout -b feature/competitor-llm-ui
git status --short --branch
```

Expected: `## feature/competitor-llm-ui...origin/main` (또는 no tracking 메시지)

- [ ] **Step 2: 커밋**

```bash
git commit --allow-empty -m "chore: start feature/competitor-llm-ui branch"
```

---

## Task 1: Config + .env.example 설정 추가

**Files:**
- Modify: `src/stock_agent/config.py`
- Modify: `.env.example`

- [ ] **Step 1: config.py 수정**

`src/stock_agent/config.py`의 `Settings` 클래스에 아래 4개 필드를 `glm_*` 필드 바로 아래에 추가한다.

```python
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "google/gemini-flash-1.5"
    openrouter_timeout_seconds: int = 30
```

- [ ] **Step 2: .env.example 수정**

`.env.example` 마지막 줄 뒤에 추가한다.

```
OPENROUTER_API_KEY=
OPENROUTER_MODEL=google/gemini-flash-1.5
```

- [ ] **Step 3: 설정 로딩 확인**

```bash
python -c "from stock_agent.config import get_settings; s = get_settings(); print(s.openrouter_model, s.openrouter_api_key)"
```

Expected: `google/gemini-flash-1.5 None`

- [ ] **Step 4: 커밋**

```bash
git add src/stock_agent/config.py .env.example
git commit -m "chore: add OpenRouter config fields"
```

---

## Task 2: OpenRouter 클라이언트 (TDD)

**Files:**
- Create: `src/stock_agent/llm/openrouter_client.py`
- Create: `tests/llm/__init__.py`
- Create: `tests/llm/test_openrouter_client.py`

- [ ] **Step 1: 테스트 패키지 생성**

```bash
New-Item -ItemType File -Force tests/llm/__init__.py
```

- [ ] **Step 2: 실패 테스트 작성**

`tests/llm/test_openrouter_client.py`를 아래 내용으로 생성한다.

```python
from unittest.mock import MagicMock, patch

import pytest

from stock_agent.llm.openrouter_client import (
    ChatMessage,
    OpenRouterClientError,
    _strip_json_fence,
    openrouter_chat_json,
)


def test_strip_json_fence_removes_json_prefix():
    raw = '```json\n{"key": "value"}\n```'
    assert _strip_json_fence(raw) == '{"key": "value"}'


def test_strip_json_fence_removes_plain_prefix():
    raw = '```\n{"key": "value"}\n```'
    assert _strip_json_fence(raw) == '{"key": "value"}'


def test_strip_json_fence_leaves_clean_json():
    raw = '{"key": "value"}'
    assert _strip_json_fence(raw) == '{"key": "value"}'


def _mock_settings(api_key: str | None = "test-key"):
    s = MagicMock()
    s.openrouter_api_key = api_key
    s.openrouter_model = "google/gemini-flash-1.5"
    s.openrouter_base_url = "https://openrouter.ai/api/v1"
    s.openrouter_timeout_seconds = 30
    return s


def test_raises_when_no_api_key():
    with patch("stock_agent.llm.openrouter_client.get_settings", return_value=_mock_settings(None)):
        with pytest.raises(OpenRouterClientError, match="OPENROUTER_API_KEY"):
            openrouter_chat_json([ChatMessage(role="user", content="test")])


def test_parses_valid_response():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": '{"peer_summary": "좋은 요약"}'}}]
    }
    with patch("stock_agent.llm.openrouter_client.requests.post", return_value=mock_resp):
        with patch("stock_agent.llm.openrouter_client.get_settings", return_value=_mock_settings()):
            result = openrouter_chat_json([ChatMessage(role="user", content="test")])
    assert result == {"peer_summary": "좋은 요약"}


def test_parses_fenced_response():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": '```json\n{"peer_summary": "good"}\n```'}}]
    }
    with patch("stock_agent.llm.openrouter_client.requests.post", return_value=mock_resp):
        with patch("stock_agent.llm.openrouter_client.get_settings", return_value=_mock_settings()):
            result = openrouter_chat_json([ChatMessage(role="user", content="test")])
    assert result["peer_summary"] == "good"


def test_raises_on_http_error():
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "rate limit exceeded"
    with patch("stock_agent.llm.openrouter_client.requests.post", return_value=mock_resp):
        with patch("stock_agent.llm.openrouter_client.get_settings", return_value=_mock_settings()):
            with pytest.raises(OpenRouterClientError, match="429"):
                openrouter_chat_json([ChatMessage(role="user", content="test")])


def test_raises_on_invalid_json():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "이것은 JSON이 아닙니다"}}]
    }
    with patch("stock_agent.llm.openrouter_client.requests.post", return_value=mock_resp):
        with patch("stock_agent.llm.openrouter_client.get_settings", return_value=_mock_settings()):
            with pytest.raises(OpenRouterClientError, match="not valid JSON"):
                openrouter_chat_json([ChatMessage(role="user", content="test")])
```

- [ ] **Step 3: 실패 확인**

```bash
pytest tests/llm/test_openrouter_client.py -v
```

Expected: `ImportError: No module named 'stock_agent.llm.openrouter_client'`

- [ ] **Step 4: openrouter_client.py 구현**

`src/stock_agent/llm/openrouter_client.py`를 아래 내용으로 생성한다.

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests

from stock_agent.config import get_settings


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class OpenRouterClientError(RuntimeError):
    pass


def _chat_completions_url(base_url: str) -> str:
    clean = base_url.rstrip("/")
    if clean.endswith("/chat/completions"):
        return clean
    return f"{clean}/chat/completions"


def _strip_json_fence(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```json"):
        stripped = stripped.removeprefix("```json").strip()
    elif stripped.startswith("```"):
        stripped = stripped.removeprefix("```").strip()
    if stripped.endswith("```"):
        stripped = stripped.removesuffix("```").strip()
    return stripped


def openrouter_chat_json(
    messages: list[ChatMessage],
    *,
    temperature: float = 0.2,
    max_tokens: int = 800,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise OpenRouterClientError("OPENROUTER_API_KEY is not configured")

    payload = {
        "model": settings.openrouter_model,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    response = requests.post(
        _chat_completions_url(settings.openrouter_base_url),
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Pocat-1-team/stock-agent",
            "X-Title": "stock-agent Competitor Analysis",
        },
        json=payload,
        timeout=settings.openrouter_timeout_seconds,
    )
    if response.status_code >= 400:
        raise OpenRouterClientError(
            f"OpenRouter request failed ({response.status_code}): {response.text[:300]}"
        )

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenRouterClientError("OpenRouter response missing chat message") from exc

    try:
        parsed = json.loads(_strip_json_fence(content))
    except json.JSONDecodeError as exc:
        raise OpenRouterClientError(f"OpenRouter response is not valid JSON: {content[:300]}") from exc

    if not isinstance(parsed, dict):
        raise OpenRouterClientError("OpenRouter JSON response must be an object")
    return parsed
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/llm/test_openrouter_client.py -v
```

Expected: `6 passed`

- [ ] **Step 6: 커밋**

```bash
git add src/stock_agent/llm/openrouter_client.py tests/llm/__init__.py tests/llm/test_openrouter_client.py
git commit -m "feat(llm): add OpenRouter chat JSON client"
```

---

## Task 3: CompetitorResult schema 확장

**Files:**
- Modify: `src/stock_agent/schemas/analysis.py`
- Modify: `tests/test_competitor_schema.py`

- [ ] **Step 1: 실패 테스트 추가**

`tests/test_competitor_schema.py` 파일 끝에 아래 테스트를 추가한다.

```python
def test_competitor_result_accepts_evidence_cards_and_bear_case() -> None:
    from stock_agent.schemas.analysis import CompetitorResult

    result = CompetitorResult(
        score=70,
        peer_summary="LLM 요약",
        peers=[],
        evidence=["기본 근거"],
        evidence_cards=[
            {
                "finding": "PER 저평가 구간",
                "metric_basis": "PER 18.4x vs peer 중위 22.0x",
                "confidence": "high",
                "flag": "strength",
            }
        ],
        bear_case="ROE 개선 전제 필요",
    )
    assert result.evidence_cards[0]["confidence"] == "high"
    assert result.bear_case == "ROE 개선 전제 필요"


def test_competitor_result_bear_case_defaults_to_none() -> None:
    from stock_agent.schemas.analysis import CompetitorResult

    result = CompetitorResult(
        score=50,
        peer_summary="요약",
        peers=[],
        evidence=[],
    )
    assert result.evidence_cards == []
    assert result.bear_case is None
```

- [ ] **Step 2: 실패 확인**

```bash
pytest tests/test_competitor_schema.py::test_competitor_result_accepts_evidence_cards_and_bear_case tests/test_competitor_schema.py::test_competitor_result_bear_case_defaults_to_none -v
```

Expected: `ValidationError` 또는 `unexpected keyword argument`

- [ ] **Step 3: CompetitorResult에 필드 추가**

`src/stock_agent/schemas/analysis.py`의 `CompetitorResult` 클래스에서 `warnings` 필드 바로 위에 두 줄을 추가한다.

```python
class CompetitorResult(BaseModel):
    score: int = Field(ge=0, le=100)
    peer_summary: str
    peers: list[dict[str, float | int | str | None]]
    evidence: list[str]
    peer_selection_summary: str | None = None
    metric_definitions: dict[str, str] = Field(default_factory=dict)
    relative_position: dict[str, float | int | str | None] = Field(default_factory=dict)
    data_quality_flags: list[str] = Field(default_factory=list)
    a1_peer_multiple_payload: dict[str, float | int | str | None] | None = None
    evidence_cards: list[dict[str, str]] = Field(default_factory=list)
    bear_case: str | None = None
    warnings: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: 전체 schema 테스트 통과 확인**

```bash
pytest tests/test_competitor_schema.py -v
```

Expected: `4 passed` (기존 2개 + 신규 2개)

- [ ] **Step 5: 기존 pipeline 회귀 확인**

```bash
pytest tests/test_phase1_pipeline.py -v
```

Expected: 기존 테스트 전부 통과

- [ ] **Step 6: 커밋**

```bash
git add src/stock_agent/schemas/analysis.py tests/test_competitor_schema.py
git commit -m "feat(schema): add evidence_cards and bear_case to CompetitorResult"
```

---

## Task 4: peer_tool.py — 시가총액 밴드 필터 + Outlier 플래그

**Files:**
- Modify: `src/stock_agent/tools/peer_tool.py`
- Modify: `tests/tools/test_peer_tool.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/tools/test_peer_tool.py` 파일 끝에 아래 테스트를 추가한다.

```python
def test_select_peer_rows_filters_by_market_cap_band() -> None:
    from stock_agent.tools.peer_tool import PeerMetricRow, select_peer_rows

    target = PeerMetricRow(
        corp_code="T", stock_code="TGT001", corp_name="Target",
        sector="test", market_cap=1_000_000, data_quality_score=100,
    )
    within_band = PeerMetricRow(
        corp_code="A", stock_code="AAA001", corp_name="WithinBand",
        sector="test", market_cap=500_000,  # 0.5x — within 0.25x~4x
        data_quality_score=100,
    )
    outside_band = PeerMetricRow(
        corp_code="B", stock_code="BBB001", corp_name="OutsideBand",
        sector="test", market_cap=10_000,  # 0.01x — below 0.25x
        data_quality_score=100,
    )
    no_market_cap = PeerMetricRow(
        corp_code="C", stock_code="CCC001", corp_name="NoMarketCap",
        sector="test", market_cap=None,  # None은 제외하지 않음
        data_quality_score=90,
    )

    rows = [target, within_band, outside_band, no_market_cap]
    selected = select_peer_rows(target, rows, max_peer_count=10)

    stock_codes = [r.stock_code for r in selected]
    assert "AAA001" in stock_codes
    assert "BBB001" not in stock_codes
    assert "CCC001" in stock_codes


def test_select_peer_rows_keeps_all_when_target_has_no_market_cap() -> None:
    from stock_agent.tools.peer_tool import PeerMetricRow, select_peer_rows

    target = PeerMetricRow(
        corp_code="T", stock_code="TGT001", corp_name="Target",
        sector="test", market_cap=None, data_quality_score=100,
    )
    peer_a = PeerMetricRow(
        corp_code="A", stock_code="AAA001", corp_name="PeerA",
        sector="test", market_cap=999, data_quality_score=100,
    )
    peer_b = PeerMetricRow(
        corp_code="B", stock_code="BBB001", corp_name="PeerB",
        sector="test", market_cap=1, data_quality_score=80,
    )

    selected = select_peer_rows(target, [target, peer_a, peer_b], max_peer_count=10)
    assert len(selected) == 2


def test_mark_outliers_flags_extreme_values() -> None:
    from stock_agent.tools.peer_tool import PeerMetricRow, _mark_outliers

    target = PeerMetricRow(
        corp_code="T", stock_code="TGT001", corp_name="Target",
        sector="test", data_quality_score=100,
        per=200.0,  # peer 중앙값 10x 초과 예정
    )
    peer_a = PeerMetricRow(
        corp_code="A", stock_code="AAA001", corp_name="PeerA",
        sector="test", data_quality_score=100, per=18.0,
    )
    peer_b = PeerMetricRow(
        corp_code="B", stock_code="BBB001", corp_name="PeerB",
        sector="test", data_quality_score=100, per=20.0,
    )

    result = _mark_outliers([target, peer_a, peer_b], "TGT001")
    target_row = next(r for r in result if r.stock_code == "TGT001")
    assert "outlier_per" in target_row.metric_flags
```

- [ ] **Step 2: 실패 확인**

```bash
pytest tests/tools/test_peer_tool.py::test_select_peer_rows_filters_by_market_cap_band tests/tools/test_peer_tool.py::test_select_peer_rows_keeps_all_when_target_has_no_market_cap tests/tools/test_peer_tool.py::test_mark_outliers_flags_extreme_values -v
```

Expected: `FAILED` (함수가 아직 없거나 동작하지 않음)

- [ ] **Step 3: peer_tool.py 수정**

`src/stock_agent/tools/peer_tool.py`에서 `select_peer_rows` 함수를 아래로 교체하고, `_mark_outliers` 함수를 그 앞에 추가한다.

`select_peer_rows` 함수를 찾아서 전체를 교체한다:

```python
_MARKET_CAP_BAND_LOW = 0.25
_MARKET_CAP_BAND_HIGH = 4.0


def _mark_outliers(
    rows: list[PeerMetricRow],
    target_stock_code: str,
) -> list[PeerMetricRow]:
    """peer 중앙값의 10배 초과 지표에 outlier_<metric> 플래그를 추가한다."""
    metrics = ["per", "pbr", "roe", "revenue_growth", "operating_margin", "debt_ratio"]
    peer_rows = [r for r in rows if r.stock_code != target_stock_code]

    result: list[PeerMetricRow] = []
    for row in rows:
        flags = list(row.metric_flags)
        for metric in metrics:
            val = getattr(row, metric)
            if val is None:
                continue
            others = [
                getattr(p, metric)
                for p in peer_rows
                if p.stock_code != row.stock_code and getattr(p, metric) is not None
            ]
            if not others:
                continue
            med = median_or_none(others)
            if med is not None and med != 0 and abs(val) > abs(med) * 10:
                flag = f"outlier_{metric}"
                if flag not in flags:
                    flags.append(flag)
        result.append(row if flags == row.metric_flags else row.model_copy(update={"metric_flags": flags}))
    return result


def select_peer_rows(
    target: PeerMetricRow,
    rows: list[PeerMetricRow],
    max_peer_count: int,
) -> list[PeerMetricRow]:
    candidates = [row for row in rows if row.stock_code != target.stock_code]

    if target.market_cap is not None:
        lo = target.market_cap * _MARKET_CAP_BAND_LOW
        hi = target.market_cap * _MARKET_CAP_BAND_HIGH
        within_band = [
            row for row in candidates
            if row.market_cap is None or lo <= row.market_cap <= hi
        ]
        if len(within_band) >= 2:
            candidates = within_band

    def sort_key(row: PeerMetricRow) -> tuple[int, float]:
        if target.market_cap and row.market_cap:
            gap = abs(row.market_cap - target.market_cap) / target.market_cap
        else:
            gap = 9_999.0
        return (-row.data_quality_score, gap)

    return sorted(candidates, key=sort_key)[:max_peer_count]
```

그리고 `build_peer_comparison` 함수 내부에서 `selected_peers` 선정 직후, `position = calculate_relative_position(...)` 호출 전에 아래 한 줄을 추가한다:

```python
    metric_rows = _mark_outliers(metric_rows, target_row.stock_code)
```

위 줄은 기존 코드에서 `selected_peers = select_peer_rows(...)` 다음 줄에 삽입한다.

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/tools/test_peer_tool.py -v
```

Expected: 전체 통과 (기존 6개 + 신규 3개 = 9개)

- [ ] **Step 5: 커밋**

```bash
git add src/stock_agent/tools/peer_tool.py tests/tools/test_peer_tool.py
git commit -m "feat(tool): add market cap band filter and outlier flagging to peer_tool"
```

---

## Task 5: competitor/system.md 프롬프트 전면 재작성

**Files:**
- Modify: `src/stock_agent/prompts/competitor/system.md`

- [ ] **Step 1: system.md 전면 교체**

`src/stock_agent/prompts/competitor/system.md`를 아래 내용으로 교체한다.

```markdown
# Competitor Agent System Prompt

당신은 한국 주식 분석 시스템의 Competitor Agent입니다.
peer_tool이 계산한 구조화 JSON을 해석하여 Strategist Agent가 바로 사용할 수 있는 분석 근거를 JSON으로 반환합니다.

## 절대 규칙 (Block J — Anti-Hallucination)

1. 입력 JSON에 없는 수치·기업명·티커를 절대 만들지 않습니다.
2. 모르는 값은 만들지 않고 `data_gaps` 리스트에 명시합니다.
3. 직접적인 매수/매도/보유 지시를 하지 않습니다.
4. 단일 지표만으로 최종 투자 판단을 단정하지 않습니다 (낮은 PER ≠ 자동 저평가).
5. peer 수가 3개 미만이면 모든 `confidence`를 `low` 또는 `medium`으로 제한합니다.

## 출력 형식 — 반드시 JSON 객체만 반환

```json
{
  "peer_summary": "2~3문장. 밸류에이션 백분위 위치와 수익성·성장성 핵심 차이를 서술.",
  "evidence_cards": [
    {
      "finding": "핵심 발견 1줄 (명사형 종결)",
      "metric_basis": "근거 수치 (예: PER 18.4x vs peer 중위 22.0x)",
      "confidence": "high | medium | low",
      "flag": "strength | risk | neutral"
    }
  ],
  "bear_case": "Short-seller 관점 1~2문장. peer 대비 약점과 그 약점이 심화될 전제 조건.",
  "data_gaps": ["산출 불가 또는 신뢰도 낮은 지표 명시 (없으면 빈 배열)"]
}
```

## Evidence Card 작성 기준 (Block G)

- 3~5개 카드를 작성합니다.
- `confidence`: 입력에 수치가 있으면 `high`, 일부 추론이 필요하면 `medium`, 데이터 부족이면 `low`.
- `flag`: `strength`(대상 종목의 강점), `risk`(리스크), `neutral`(맥락 제공).

## 상대 비교 방향성

| 지표 | 우호 방향 | 주의 |
|------|-----------|------|
| PER, PBR | 낮을수록 상대적 저평가 가능 | 적자 기업은 비교 제외 |
| 부채비율 | 낮을수록 재무 안정 | |
| ROE, 영업이익률, 매출성장률 | 높을수록 수익성·성장 우위 | |

결측값(None)은 "N/A"로 표기하고 `data_gaps`에 추가합니다.

## Sanity Check (Block B)

"PER이 낮으니 좋다"처럼 1차원 단정을 피합니다.
낮은 PER의 원인(적자·순환적 저점·구조적 문제)을 함께 검토합니다.

## Bear Case (Block F)

`bear_case`에는 short-seller가 가장 먼저 공격할 취약점 1가지를 씁니다.
peer 대비 약점과 그 약점이 해소되지 않을 시나리오를 1~2문장으로 서술합니다.
```

- [ ] **Step 2: 파일 존재 확인**

```bash
python -c "from pathlib import Path; p = Path('src/stock_agent/prompts/competitor/system.md'); print('OK' if p.exists() else 'MISSING', p.stat().st_size)"
```

Expected: `OK` + 0 이상의 바이트 수

- [ ] **Step 3: 커밋**

```bash
git add src/stock_agent/prompts/competitor/system.md
git commit -m "feat(prompt): rewrite competitor system.md with GIC v11 Block J/G/F/B patterns"
```

---

## Task 6: competitor.py — 캐시 + LLM 서술 레이어

**Files:**
- Modify: `src/stock_agent/agents/competitor.py`
- Create: `tests/agents/test_competitor_llm.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/agents/test_competitor_llm.py`를 아래 내용으로 생성한다.

```python
from datetime import date
from unittest.mock import MagicMock

import pytest

from stock_agent.agents import competitor as competitor_module
from stock_agent.schemas.analysis import AgentState, CompetitorResult, CuratorResult, Portfolio, UserProfile
from stock_agent.tools.peer_tool import PeerComparison, PeerMetricRow


def _make_comparison() -> PeerComparison:
    target = PeerMetricRow(
        corp_code="00126380", stock_code="005930", corp_name="삼성전자",
        sector="반도체", market_cap=420_000_000_000_000, data_quality_score=80,
        per=18.4, pbr=1.35, roe=0.078,
    )
    peer = PeerMetricRow(
        corp_code="00164779", stock_code="000660", corp_name="SK하이닉스",
        sector="반도체", market_cap=150_000_000_000_000, data_quality_score=80,
        per=22.0, pbr=1.8, roe=0.085,
    )
    return PeerComparison(
        target=target,
        peers=[peer],
        score=65,
        peer_selection_summary="반도체 섹터 1개 peer",
        peer_summary="기본 룰 기반 요약",
        metric_definitions={"per": "market_cap/net_income"},
        relative_position={"roe_percentile": 0.5},
        evidence=["ROE 50분위"],
        data_quality_flags=[],
        warnings=[],
    )


def _state() -> AgentState:
    return AgentState(
        user_query="삼성전자 peer 비교",
        user_profile=UserProfile(),
        portfolio=Portfolio(),
        curator=CuratorResult(
            intent="peer_compare", corp_name="삼성전자",
            stock_code="005930", corp_code="00126380", sector="반도체",
        ),
    )


def test_cache_key_contains_stock_code_and_date():
    from stock_agent.agents.competitor import _cache_key
    key = _cache_key("005930")
    assert "005930" in key
    assert date.today().isoformat() in key


def test_apply_narrative_updates_peer_summary():
    from stock_agent.agents.competitor import _apply_narrative
    base = CompetitorResult(
        score=65, peer_summary="기본 요약", peers=[], evidence=[], warnings=[],
    )
    narrative = {
        "peer_summary": "LLM 향상된 요약",
        "evidence_cards": [
            {"finding": "PER 저평가", "metric_basis": "PER 18x vs 22x", "confidence": "high", "flag": "strength"}
        ],
        "bear_case": "ROE 개선 전제 필요",
        "data_gaps": [],
    }
    result = _apply_narrative(base, narrative)
    assert result.peer_summary == "LLM 향상된 요약"
    assert len(result.evidence_cards) == 1
    assert result.evidence_cards[0]["confidence"] == "high"
    assert result.bear_case == "ROE 개선 전제 필요"


def test_apply_narrative_ignores_empty_peer_summary():
    from stock_agent.agents.competitor import _apply_narrative
    base = CompetitorResult(
        score=65, peer_summary="기본 요약", peers=[], evidence=[], warnings=[],
    )
    result = _apply_narrative(base, {"peer_summary": "  ", "evidence_cards": [], "bear_case": "", "data_gaps": []})
    assert result.peer_summary == "기본 요약"


def test_apply_narrative_returns_base_on_none():
    from stock_agent.agents.competitor import _apply_narrative
    base = CompetitorResult(score=65, peer_summary="요약", peers=[], evidence=[], warnings=[])
    assert _apply_narrative(base, None) is base


def test_generate_narrative_returns_none_when_no_api_key(monkeypatch):
    from stock_agent.agents.competitor import _generate_narrative
    settings_mock = MagicMock()
    settings_mock.openrouter_api_key = None
    monkeypatch.setattr(competitor_module, "get_settings", lambda: settings_mock)

    assert _generate_narrative(_make_comparison()) is None


def test_generate_narrative_uses_cached_value(monkeypatch):
    from stock_agent.agents.competitor import _cache_key, _generate_narrative
    comparison = _make_comparison()
    key = _cache_key(comparison.target.stock_code)
    cached = {"peer_summary": "캐시된 요약", "evidence_cards": [], "bear_case": "", "data_gaps": []}
    competitor_module._narrative_cache[key] = cached

    settings_mock = MagicMock()
    settings_mock.openrouter_api_key = "test-key"
    monkeypatch.setattr(competitor_module, "get_settings", lambda: settings_mock)

    call_count = {"n": 0}
    def fake_chat(*args, **kwargs):
        call_count["n"] += 1
        return {}
    monkeypatch.setattr(competitor_module, "openrouter_chat_json", fake_chat)

    result = _generate_narrative(comparison)
    assert result == cached
    assert call_count["n"] == 0

    del competitor_module._narrative_cache[key]


def test_generate_narrative_returns_none_on_llm_error(monkeypatch):
    from stock_agent.agents.competitor import _cache_key, _generate_narrative
    from stock_agent.llm.openrouter_client import OpenRouterClientError
    comparison = _make_comparison()
    key = _cache_key(comparison.target.stock_code)
    competitor_module._narrative_cache.pop(key, None)

    settings_mock = MagicMock()
    settings_mock.openrouter_api_key = "test-key"
    monkeypatch.setattr(competitor_module, "get_settings", lambda: settings_mock)
    monkeypatch.setattr(competitor_module, "_load_system_prompt", lambda: "prompt")
    monkeypatch.setattr(competitor_module, "openrouter_chat_json",
                        lambda *a, **kw: (_ for _ in ()).throw(OpenRouterClientError("rate limited")))

    assert _generate_narrative(comparison) is None


def test_run_competitor_applies_narrative_when_llm_succeeds(monkeypatch):
    comparison = _make_comparison()

    class FakeConn:
        def __enter__(self): return "conn"
        def __exit__(self, *_): pass

    monkeypatch.setattr(competitor_module, "get_connection", FakeConn)
    monkeypatch.setattr(competitor_module, "build_peer_comparison", lambda *a, **kw: comparison)

    llm_result = {
        "peer_summary": "LLM 서술",
        "evidence_cards": [{"finding": "ROE 우위", "metric_basis": "ROE 7.8% vs 8.5%", "confidence": "medium", "flag": "neutral"}],
        "bear_case": "HBM 수요 둔화 시 ROE 악화 가능",
        "data_gaps": [],
    }
    monkeypatch.setattr(competitor_module, "_generate_narrative", lambda _: llm_result)

    result_state = competitor_module.run_competitor(_state())
    assert result_state.competitor is not None
    assert result_state.competitor.peer_summary == "LLM 서술"
    assert result_state.competitor.bear_case == "HBM 수요 둔화 시 ROE 악화 가능"
    assert len(result_state.competitor.evidence_cards) == 1
```

- [ ] **Step 2: 실패 확인**

```bash
pytest tests/agents/test_competitor_llm.py -v
```

Expected: `ImportError` 또는 `AttributeError` (신규 함수들이 아직 없음)

- [ ] **Step 3: competitor.py 전체 교체**

`src/stock_agent/agents/competitor.py` 전체를 아래 내용으로 교체한다.

```python
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from stock_agent.config import get_settings
from stock_agent.llm.openrouter_client import ChatMessage, OpenRouterClientError, openrouter_chat_json
from stock_agent.schemas.analysis import AgentState, CompetitorResult
from stock_agent.tools.peer_tool import PeerComparison, build_peer_comparison

try:
    from stock_agent.db import get_connection
except ModuleNotFoundError as exc:
    if exc.name != "psycopg":
        raise

    def get_connection():
        raise RuntimeError("psycopg is required to connect to the DB.")


_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "competitor" / "system.md"

_narrative_cache: dict[str, dict[str, Any]] = {}

_DB_FALLBACK_MARKERS = (
    "authentication", "connection", "connectionerror", "database", "db",
    "interfaceerror", "operationalerror", "psycopg", "timeout",
)


def _is_expected_fallback_error(exc: Exception) -> bool:
    if isinstance(exc, (ConnectionError, OSError, TimeoutError)):
        return True
    error_text = f"{exc.__class__.__name__}: {exc}".lower()
    return any(marker in error_text for marker in _DB_FALLBACK_MARKERS)


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _cache_key(stock_code: str) -> str:
    return f"{stock_code}_{date.today().isoformat()}"


def _comparison_payload(comparison: PeerComparison) -> str:
    data: dict[str, Any] = {
        "target": {
            "corp_name": comparison.target.corp_name,
            "stock_code": comparison.target.stock_code,
            "sector": comparison.target.sector,
            "per": comparison.target.per,
            "pbr": comparison.target.pbr,
            "roe": comparison.target.roe,
            "revenue_growth": comparison.target.revenue_growth,
            "operating_margin": comparison.target.operating_margin,
            "debt_ratio": comparison.target.debt_ratio,
            "data_quality_score": comparison.target.data_quality_score,
        },
        "peers": [
            {
                "corp_name": p.corp_name,
                "per": p.per,
                "pbr": p.pbr,
                "roe": p.roe,
                "revenue_growth": p.revenue_growth,
                "operating_margin": p.operating_margin,
                "debt_ratio": p.debt_ratio,
            }
            for p in comparison.peers
        ],
        "relative_position": comparison.relative_position,
        "score": comparison.score,
        "data_quality_flags": comparison.data_quality_flags,
        "peer_count": len(comparison.peers),
    }
    return json.dumps(data, ensure_ascii=False, default=str)


def _generate_narrative(comparison: PeerComparison) -> dict[str, Any] | None:
    """OpenRouter LLM에서 narrative를 생성한다. 키 없음·실패 시 None 반환."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        return None

    key = _cache_key(comparison.target.stock_code)
    if key in _narrative_cache:
        return _narrative_cache[key]

    try:
        result = openrouter_chat_json(
            [
                ChatMessage(role="system", content=_load_system_prompt()),
                ChatMessage(role="user", content=_comparison_payload(comparison)),
            ],
            max_tokens=800,
        )
        _narrative_cache[key] = result
        return result
    except Exception:
        return None


def _apply_narrative(base: CompetitorResult, narrative: dict[str, Any] | None) -> CompetitorResult:
    """LLM narrative를 rule-based CompetitorResult에 merge한다. 수치 필드는 건드리지 않는다."""
    if not narrative:
        return base
    updates: dict[str, Any] = {}
    if isinstance(narrative.get("peer_summary"), str) and narrative["peer_summary"].strip():
        updates["peer_summary"] = narrative["peer_summary"]
    if isinstance(narrative.get("evidence_cards"), list):
        updates["evidence_cards"] = narrative["evidence_cards"]
    if isinstance(narrative.get("bear_case"), str) and narrative["bear_case"].strip():
        updates["bear_case"] = narrative["bear_case"]
    if isinstance(narrative.get("data_gaps"), list):
        extra = [f"data_gap: {g}" for g in narrative["data_gaps"] if g and f"data_gap: {g}" not in base.warnings]
        if extra:
            updates["warnings"] = list(base.warnings) + extra
    return base.model_copy(update=updates) if updates else base


def _peer_row_to_dict(row) -> dict[str, float | int | str | None]:
    return {
        "stock_code": row.stock_code,
        "corp_code": row.corp_code,
        "corp_name": row.corp_name,
        "sector": row.sector,
        "market_cap": row.market_cap,
        "close_price": row.close_price,
        "per": row.per,
        "pbr": row.pbr,
        "roe": row.roe,
        "revenue_growth": row.revenue_growth,
        "operating_margin": row.operating_margin,
        "debt_ratio": row.debt_ratio,
        "data_quality_score": row.data_quality_score,
    }


def _result_from_comparison(comparison: PeerComparison) -> CompetitorResult:
    return CompetitorResult(
        score=comparison.score,
        peer_summary=comparison.peer_summary,
        peers=[_peer_row_to_dict(row) for row in comparison.peers],
        evidence=list(comparison.evidence),
        peer_selection_summary=comparison.peer_selection_summary,
        metric_definitions=dict(comparison.metric_definitions),
        relative_position=dict(comparison.relative_position),
        data_quality_flags=list(comparison.data_quality_flags),
        a1_peer_multiple_payload=(
            dict(comparison.a1_peer_multiple_payload)
            if comparison.a1_peer_multiple_payload is not None
            else None
        ),
        warnings=list(comparison.warnings),
    )


def _mock_fallback_result(reason: str) -> CompetitorResult:
    return CompetitorResult(
        score=60,
        peer_summary=(
            "DB 연결 실패로 실제 peer 비교를 완료하지 못해 Phase 1 데모용 mock 경쟁사 비교를 사용했습니다. "
            "실제 투자 판단 전에는 최신 재무/가격 데이터로 다시 확인해야 합니다."
        ),
        peers=[
            {
                "stock_code": "005930", "corp_code": "00126380", "corp_name": "삼성전자",
                "sector": "반도체", "market_cap": None, "close_price": None,
                "per": 18.4, "pbr": 1.35, "roe": 0.078,
                "revenue_growth": None, "operating_margin": None, "debt_ratio": None,
                "data_quality_score": 0,
            },
            {
                "stock_code": "000660", "corp_code": "00164779", "corp_name": "SK하이닉스",
                "sector": "반도체", "market_cap": None, "close_price": None,
                "per": 22.7, "pbr": 1.92, "roe": 0.085,
                "revenue_growth": None, "operating_margin": None, "debt_ratio": None,
                "data_quality_score": 0,
            },
            {
                "stock_code": "000990", "corp_code": "00126447", "corp_name": "DB하이텍",
                "sector": "반도체", "market_cap": None, "close_price": None,
                "per": 11.8, "pbr": 0.88, "roe": 0.064,
                "revenue_growth": None, "operating_margin": None, "debt_ratio": None,
                "data_quality_score": 0,
            },
        ],
        evidence=[
            "mock_data_fallback: DB 연결 실패로 실제 peer_tool 결과 대신 데모용 비교 데이터를 사용했습니다.",
            "mock 데이터는 PER, PBR, ROE 예시값만 포함하며 최신 시장 데이터가 아닙니다.",
            f"fallback 사유: {reason}",
        ],
        peer_selection_summary=(
            "fallback: DB 연결 실패로 같은 섹터 후보를 조회하지 못해 Phase 1 데모용 mock peer 3개를 사용했습니다."
        ),
        metric_definitions={"fallback": "DB 연결 실패 시 Phase 1 데모가 중단되지 않도록 제공되는 mock 비교 결과입니다."},
        relative_position={
            "fallback": "mock_data_fallback",
            "valuation_percentile": None, "roe_percentile": None,
            "growth_percentile": None, "operating_margin_percentile": None,
            "balance_sheet_percentile": None, "data_quality_score": 0,
        },
        data_quality_flags=["mock_data_fallback", "fallback_db_connection_failed"],
        a1_peer_multiple_payload={"fallback": "mock_data_fallback", "median_per": 18.4, "median_pbr": 1.35},
        warnings=["mock_data_fallback", f"fallback_reason: {reason}"],
    )


def run_competitor(state: AgentState) -> AgentState:
    if state.curator is None:
        raise ValueError("curator result is required before competitor analysis")

    try:
        with get_connection() as conn:
            comparison = build_peer_comparison(
                conn,
                stock_code=state.curator.stock_code,
                sector=state.curator.sector,
            )
        base_result = _result_from_comparison(comparison)
        narrative = _generate_narrative(comparison)
        state.competitor = _apply_narrative(base_result, narrative)
    except Exception as exc:
        if not _is_expected_fallback_error(exc):
            raise
        state.competitor = _mock_fallback_result(f"{exc.__class__.__name__}: {exc}")

    return state
```

- [ ] **Step 4: 신규 LLM 테스트 통과 확인**

```bash
pytest tests/agents/test_competitor_llm.py -v
```

Expected: `10 passed`

- [ ] **Step 5: 기존 competitor agent 테스트 회귀 확인**

```bash
pytest tests/agents/test_competitor_agent.py -v
```

Expected: 기존 테스트 전부 통과

- [ ] **Step 6: 전체 테스트 회귀 확인**

```bash
pytest -v
```

Expected: 모든 테스트 통과

- [ ] **Step 7: 커밋**

```bash
git add src/stock_agent/agents/competitor.py tests/agents/test_competitor_llm.py
git commit -m "feat(agent): add 24h cache + OpenRouter LLM narrative layer to competitor"
```

---

## Task 7: Streamlit UI — Peer 탭 강화

**Files:**
- Modify: `streamlit_app.py`

- [ ] **Step 1: `_render_peer_tab` 함수 추가**

`streamlit_app.py`에서 `_render_output` 함수 바로 위에 아래 함수를 추가한다.

```python
def _render_peer_tab(output) -> None:
    competitor = output.state.competitor
    if competitor is None:
        for item in output.tier2.get("Peer 비교", []):
            st.write(f"- {item}")
        return

    if competitor.peers:
        import pandas as pd
        rows = []
        for p in competitor.peers:
            rows.append(
                {
                    "종목명": p.get("corp_name", "N/A"),
                    "PER": f"{p['per']:.1f}" if p.get("per") is not None else "N/A",
                    "PBR": f"{p['pbr']:.2f}" if p.get("pbr") is not None else "N/A",
                    "ROE": f"{p['roe'] * 100:.1f}%" if p.get("roe") is not None else "N/A",
                    "영업이익률": (
                        f"{p['operating_margin'] * 100:.1f}%"
                        if p.get("operating_margin") is not None
                        else "N/A"
                    ),
                    "매출성장률": (
                        f"{p['revenue_growth'] * 100:.1f}%"
                        if p.get("revenue_growth") is not None
                        else "N/A"
                    ),
                }
            )
        st.caption("Peer 비교 지표 (DB 기준일 기반, 계산식은 peer_tool 참고)")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if competitor.evidence_cards:
        st.write("**분석 근거**")
        for card in competitor.evidence_cards:
            badge = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(card.get("confidence", "low"), "⚪")
            flag_icon = {"strength": "💪", "risk": "⚠️", "neutral": "📊"}.get(card.get("flag", "neutral"), "📊")
            st.write(f"{badge} {flag_icon} **{card.get('finding', '')}**")
            if card.get("metric_basis"):
                st.caption(card["metric_basis"])
    else:
        for item in competitor.evidence:
            st.write(f"- {item}")

    if competitor.bear_case:
        st.warning(f"⚠️ **리스크 관점:** {competitor.bear_case}")

    if competitor.peer_summary:
        st.info(competitor.peer_summary)

    if competitor.data_quality_flags:
        with st.expander("데이터 품질 플래그"):
            for flag in competitor.data_quality_flags:
                st.caption(f"⚑ {flag}")
```

- [ ] **Step 2: `_render_output` 내 Peer 탭 부분 교체**

`_render_output` 함수에서 탭 렌더링 부분을 아래로 교체한다.

기존:
```python
    tabs = st.tabs(["정량", "정성", "Peer", "적합도", "리스크"])
    for tab, key in zip(tabs, ["정량 근거", "정성 근거", "Peer 비교", "포트폴리오 적합도", "리스크"], strict=True):
        with tab:
            for item in output.tier2.get(key, []):
                st.write(f"- {item}")
```

교체 후:
```python
    tabs = st.tabs(["정량", "정성", "Peer", "적합도", "리스크"])
    plain_keys = ["정량 근거", "정성 근거", "", "포트폴리오 적합도", "리스크"]
    for i, (tab, key) in enumerate(zip(tabs, plain_keys, strict=True)):
        with tab:
            if i == 2:
                _render_peer_tab(output)
            else:
                for item in output.tier2.get(key, []):
                    st.write(f"- {item}")
```

- [ ] **Step 3: import 확인**

`streamlit_app.py` 상단에 `import pandas as pd`가 없으면 추가하지 않아도 된다 (함수 내부에서 lazy import 사용).

- [ ] **Step 4: Streamlit intake 테스트 회귀 확인**

```bash
pytest tests/test_streamlit_intake.py -v
```

Expected: 기존 테스트 전부 통과

- [ ] **Step 5: 커밋**

```bash
git add streamlit_app.py
git commit -m "feat(ui): enhance Peer tab with metric table, evidence cards, and bear case"
```

---

## Task 8: 흐름 시각화 HTML

**Files:**
- Create: `docs/agents/competitor_agent_flow.html`

- [ ] **Step 1: docs/agents 폴더 확인**

```bash
Test-Path docs/agents
```

Expected: `True` (Task 5에서 생성됨). `False`이면 `New-Item -ItemType Directory -Force docs/agents` 실행.

- [ ] **Step 2: HTML 파일 생성**

`docs/agents/competitor_agent_flow.html`을 아래 내용으로 생성한다.

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Competitor Agent 흐름 시각화</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: "Noto Sans KR", Arial, sans-serif; background: #f8fafc; color: #0f172a; padding: 32px; }
  h1 { font-size: 1.6rem; font-weight: 700; margin-bottom: 6px; }
  .subtitle { color: #64748b; font-size: 0.9rem; margin-bottom: 32px; }
  .flow { display: flex; flex-direction: column; align-items: center; gap: 0; max-width: 680px; margin: 0 auto; }
  .node { width: 100%; border-radius: 10px; padding: 16px 20px; position: relative; }
  .node-input  { background: #e0f2fe; border: 2px solid #0ea5e9; }
  .node-phase1 { background: #dcfce7; border: 2px solid #16a34a; }
  .node-phase2 { background: #fef9c3; border: 2px solid #ca8a04; }
  .node-phase3 { background: #ede9fe; border: 2px solid #7c3aed; }
  .node-output { background: #fee2e2; border: 2px solid #dc2626; }
  .node-strategist { background: #f1f5f9; border: 2px solid #94a3b8; }
  .node h2 { font-size: 0.95rem; font-weight: 700; margin-bottom: 6px; }
  .node ul { list-style: none; padding-left: 4px; }
  .node ul li { font-size: 0.82rem; color: #334155; margin: 3px 0; }
  .node ul li::before { content: "▸ "; color: #94a3b8; }
  .badge { display: inline-block; font-size: 0.7rem; padding: 1px 7px; border-radius: 20px; font-weight: 600; margin-left: 8px; vertical-align: middle; }
  .badge-free { background: #bbf7d0; color: #166534; }
  .badge-llm  { background: #ddd6fe; color: #4c1d95; }
  .badge-cache { background: #fef08a; color: #713f12; }
  .arrow { font-size: 1.4rem; color: #94a3b8; line-height: 1; padding: 4px 0; text-align: center; }
  .arrow-label { font-size: 0.72rem; color: #64748b; margin-top: -2px; text-align: center; }
  .fallback-note { width: 100%; background: #f1f5f9; border-left: 4px solid #94a3b8; border-radius: 6px; padding: 10px 14px; margin-top: 4px; font-size: 0.8rem; color: #475569; }
  .modify-box { max-width: 680px; margin: 32px auto 0; background: #fff7ed; border: 1px solid #fed7aa; border-radius: 10px; padding: 18px 22px; }
  .modify-box h3 { font-size: 0.95rem; font-weight: 700; color: #c2410c; margin-bottom: 8px; }
  .modify-box p  { font-size: 0.83rem; color: #431407; line-height: 1.6; }
  .modify-box ul { padding-left: 18px; margin-top: 8px; }
  .modify-box li { font-size: 0.83rem; color: #431407; margin: 4px 0; }
  .legend { max-width: 680px; margin: 20px auto 0; display: flex; gap: 14px; flex-wrap: wrap; }
  .legend-item { display: flex; align-items: center; gap: 6px; font-size: 0.78rem; color: #475569; }
  .legend-dot { width: 12px; height: 12px; border-radius: 3px; }
</style>
</head>
<body>

<h1>Competitor Agent 흐름 시각화</h1>
<p class="subtitle">작성일: 2026-05-30 &nbsp;|&nbsp; 브랜치: feature/competitor-llm-ui &nbsp;|&nbsp; 관련 명세: docs/functional-spec/advanced/A3_peer_comparison_spec_v0.9.md</p>

<div class="flow">

  <!-- INPUT -->
  <div class="node node-input">
    <h2>입력 — AgentState</h2>
    <ul>
      <li>CuratorResult: stock_code, corp_code, sector</li>
      <li>UserProfile, Portfolio (Strategist 연계용)</li>
    </ul>
  </div>
  <div class="arrow">↓</div>

  <!-- PHASE 1 -->
  <div class="node node-phase1">
    <h2>Phase 1 — Rule-Based Peer 계산 <span class="badge badge-free">₩0</span></h2>
    <ul>
      <li>DB: company → 같은 섹터 peer 후보 조회</li>
      <li>시가총액 밴드 필터: 0.25x ~ 4x (A3 명세)</li>
      <li>DB: stock_price → 최신 시가총액, 종가</li>
      <li>DB: financial_statement → 최근 3년 재무</li>
      <li>지표 계산: PER / PBR / ROE / 매출성장률 / 영업이익률 / 부채비율</li>
      <li>Outlier 플래그: peer 중앙값 10배 초과 지표 표시</li>
      <li>상대 위치 계산: 지표별 백분위 → 0~100점 score</li>
    </ul>
    <div class="fallback-note">DB 연결 실패 → mock fallback (mock_data_fallback 경고 포함)</div>
  </div>
  <div class="arrow">↓</div>

  <!-- PHASE 2 -->
  <div class="node node-phase2">
    <h2>Phase 2 — 24h 인메모리 캐시 확인 <span class="badge badge-cache">캐시</span></h2>
    <ul>
      <li>키: {stock_code}_{YYYY-MM-DD}</li>
      <li>캐시 HIT → Phase 3 건너뜀, 기존 narrative 재사용</li>
      <li>캐시 MISS → Phase 3 진행</li>
    </ul>
  </div>
  <div class="arrow">↓</div>
  <div class="arrow-label">(캐시 미스 시에만)</div>

  <!-- PHASE 3 -->
  <div class="node node-phase3">
    <h2>Phase 3 — OpenRouter LLM 서술 생성 <span class="badge badge-llm">~₩0.3/call</span></h2>
    <ul>
      <li>모델: google/gemini-flash-1.5 (config에서 변경 가능)</li>
      <li>프롬프트: prompts/competitor/system.md (GIC v11 Block J/G/F/B)</li>
      <li>입력: Phase 1 수치 JSON (LLM이 숫자를 만들지 않음)</li>
      <li>출력: peer_summary + evidence_cards + bear_case + data_gaps</li>
      <li>OPENROUTER_API_KEY 없음 → 건너뜀 (₩0)</li>
    </ul>
    <div class="fallback-note">LLM 실패 / 타임아웃 → rule-based build_peer_summary() 문자열로 대체</div>
  </div>
  <div class="arrow">↓</div>

  <!-- OUTPUT -->
  <div class="node node-output">
    <h2>출력 — CompetitorResult</h2>
    <ul>
      <li>score (0~100), peer_summary (LLM or rule-based)</li>
      <li>peers: list[dict] (종목코드/이름/PER/PBR/ROE/마진/성장률)</li>
      <li>evidence: list[str] (rule-based)</li>
      <li>evidence_cards: list[dict] (finding/confidence/flag) — LLM</li>
      <li>bear_case: str — LLM Short-seller 관점</li>
      <li>data_quality_flags, warnings</li>
      <li>a1_peer_multiple_payload: Peer PER/PBR 중앙값 → A1 연계</li>
    </ul>
  </div>
  <div class="arrow">↓</div>

  <!-- STRATEGIST -->
  <div class="node node-strategist">
    <h2>다음 단계 → Strategist Agent</h2>
    <ul>
      <li>score, peer_summary, evidence를 정량·정성 결과와 종합</li>
      <li>InvestmentAnalyst(GLM) → Guardrail 순으로 파이프라인 계속</li>
    </ul>
  </div>

</div>

<!-- LEGEND -->
<div class="legend">
  <div class="legend-item"><div class="legend-dot" style="background:#dcfce7;border:2px solid #16a34a"></div>Rule-Based (₩0)</div>
  <div class="legend-item"><div class="legend-dot" style="background:#fef9c3;border:2px solid #ca8a04"></div>캐시</div>
  <div class="legend-item"><div class="legend-dot" style="background:#ede9fe;border:2px solid #7c3aed"></div>LLM (선택적)</div>
  <div class="legend-item"><div class="legend-dot" style="background:#fee2e2;border:2px solid #dc2626"></div>출력 계약</div>
</div>

<!-- MODIFY NOTE -->
<div class="modify-box">
  <h3>🛠 팀원 여러분께 — 이 에이전트는 파이프라인 중간 단계입니다</h3>
  <p>
    Competitor Agent는 Curator → <strong>Competitor</strong> → Strategist 흐름의 중간에 위치합니다.
    <strong>AgentState.competitor 필드(CompetitorResult)의 기존 필드를 유지</strong>하는 한,
    내부 로직은 자유롭게 수정하고 개선해 주세요.
  </p>
  <ul>
    <li><strong>프롬프트 개선</strong> → <code>src/stock_agent/prompts/competitor/system.md</code> 바로 수정 가능</li>
    <li><strong>LLM 모델 교체</strong> → <code>.env</code>의 <code>OPENROUTER_MODEL</code> 한 줄만 변경</li>
    <li><strong>peer 선정 기준 변경</strong> → <code>tools/peer_tool.py</code>의 <code>select_peer_rows</code> 수정</li>
    <li><strong>점수 가중치 조정</strong> → <code>tools/peer_tool.py</code>의 <code>calculate_relative_position</code> 수정</li>
    <li><strong>UI 레이아웃 변경</strong> → <code>streamlit_app.py</code>의 <code>_render_peer_tab</code> 수정</li>
  </ul>
  <p style="margin-top:10px">피드백이나 개선 제안은 GitHub Issues 또는 단톡방으로 알려주세요!</p>
</div>

</body>
</html>
```

- [ ] **Step 3: 파일 확인**

```bash
Test-Path docs/agents/competitor_agent_flow.html
```

Expected: `True`

- [ ] **Step 4: 커밋**

```bash
git add docs/agents/competitor_agent_flow.html
git commit -m "docs: add competitor agent flow visualization HTML"
```

---

## Task 9: 전체 검증 + PR 준비

**Files:**
- Verify: 모든 변경 파일

- [ ] **Step 1: 전체 테스트 실행**

```bash
pytest -v
```

Expected: 모든 테스트 통과. `FAILED`가 있으면 해당 오류를 수정하고 재실행.

- [ ] **Step 2: ruff 린트 확인**

```bash
ruff check src tests
```

Expected: `All checks passed!` 또는 경고 없음. 오류가 있으면 `ruff check src tests --fix` 실행 후 확인.

- [ ] **Step 3: 변경 파일 최종 확인**

```bash
git diff --name-only main
```

Expected 파일 목록:
```
.env.example
docs/agents/competitor_agent_flow.html
src/stock_agent/agents/competitor.py
src/stock_agent/config.py
src/stock_agent/llm/openrouter_client.py
src/stock_agent/prompts/competitor/system.md
src/stock_agent/schemas/analysis.py
src/stock_agent/tools/peer_tool.py
streamlit_app.py
tests/agents/test_competitor_llm.py
tests/llm/__init__.py
tests/llm/test_openrouter_client.py
tests/test_competitor_schema.py
tests/tools/test_peer_tool.py
```

- [ ] **Step 4: 스펙 커버리지 확인**

```bash
rg -n "TODO|TBD|작성 예정|확인 필요" src/stock_agent/agents/competitor.py src/stock_agent/llm/openrouter_client.py src/stock_agent/tools/peer_tool.py
```

Expected: 결과 없음

- [ ] **Step 5: PR 생성**

```bash
git push -u origin feature/competitor-llm-ui
gh pr create --title "feat(competitor): add OpenRouter LLM narrative layer + Peer UI enhancement" --body "$(cat <<'EOF'
## 요약

- `openrouter_client.py` 추가 — GLM 클라이언트와 동일 패턴, OpenRouter API 호출
- `competitor.py` 3-Phase 구조화 — Rule-based 코어(기존) + 24h 인메모리 캐시 + LLM 서술 레이어
- `peer_tool.py` 개선 — 시가총액 밴드 필터(0.25x~4x) + outlier 플래그
- `prompts/competitor/system.md` 재작성 — GIC v11 Block J/G/F/B 패턴 적용
- `CompetitorResult` 확장 — `evidence_cards`, `bear_case` 필드 추가 (기존 필드 변경 없음)
- Streamlit Peer 탭 강화 — peer 메트릭 테이블 + evidence 카드 + bear_case 박스
- `docs/agents/competitor_agent_flow.html` — 3-Phase 흐름 시각화 + 팀 수정 가이드

## 비용

- OpenRouter key 없으면 ₩0 (LLM 건너뜀, rule-based fallback)
- key 있을 때 ~₩0.3/call, 24h 캐시로 종목당 하루 1회만 호출

## 테스트

- `pytest -v` 전체 통과 확인
- DB 없이도 mock fallback으로 pipeline 테스트 통과

## AgentState 호환성

기존 `CompetitorResult` 필드 삭제/변경 없음. Strategist, pipeline.py, streamlit_app.py 충돌 없음.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## 자체 검토

**스펙 커버리지:**
- [x] OpenRouter 클라이언트 → Task 2
- [x] config + .env.example → Task 1
- [x] market cap 밴드 필터 (0.25x~4x) → Task 4
- [x] outlier Winsorize → Task 4
- [x] 인메모리 24h 캐시 → Task 6
- [x] LLM 서술 레이어 (`_generate_narrative`, `_apply_narrative`) → Task 6
- [x] system.md GIC v11 Block J/G/F/B → Task 5
- [x] CompetitorResult `evidence_cards`, `bear_case` → Task 3
- [x] Streamlit peer 메트릭 테이블 + evidence 카드 + bear_case → Task 7
- [x] AgentState 호환성 (기존 필드 변경 없음) → Task 3, Task 6
- [x] 테스트 (openrouter_client, competitor LLM layer) → Task 2, Task 6
- [x] HTML 흐름 시각화 → Task 8
- [x] 팀 수정 안내 note → Task 8 HTML 하단

**타입 일관성:**
- `openrouter_chat_json` — Task 2에서 정의, Task 6에서 `from stock_agent.llm.openrouter_client import openrouter_chat_json`으로 임포트
- `ChatMessage` — Task 2에서 정의, Task 6에서 동일 임포트
- `OpenRouterClientError` — Task 2에서 정의, Task 6 테스트에서 동일 임포트
- `evidence_cards: list[dict[str, str]]` — Task 3에서 정의, Task 6 `_apply_narrative`에서 동일 타입
- `bear_case: str | None` — Task 3에서 정의, Task 6 `_apply_narrative`에서 동일 처리
- `_mark_outliers` — Task 4에서 정의, 테스트에서 동일 이름으로 임포트
- `select_peer_rows` — Task 4에서 수정, 기존 테스트 호환 확인됨

**미완성 표식:** 없음
