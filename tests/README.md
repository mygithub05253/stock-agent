# `tests/` - 자동 회귀 테스트

> Agent, LangGraph, RAG, MCP, Streamlit 입력과 결과 렌더링의 동작 계약을 검증합니다.

## 폴더 소개

- **What:** 단위·통합·회귀 테스트를 도메인별로 배치합니다.
- **Why:** Agent 하나의 변경이 최종 신호, Guardrail, UI 입력 계약을 깨뜨리지 않게 합니다.
- 루트 테스트는 전체 파이프라인과 공통 출력 계약을 검증합니다.
- 하위 폴더는 Agent, LLM, MCP, RAG, Tool을 독립적으로 검증합니다.
- 네트워크·API 키가 필요한 smoke test는 marker 또는 조건부 skip을 사용합니다.

## 기술 스택

pytest, monkeypatch, Pydantic fixture, 규칙 기반 fake 데이터를 사용합니다.

## 실행

```bash
python -m pytest
python -m pytest tests/test_phase1_pipeline.py -v
python -m pytest -m openrouter_smoke
```

현재 로컬 Anaconda 환경에서는 `tqdm/importlib_metadata` 메타데이터 문제로 RAG 2개 파일이 수집 단계에서 실패할 수 있습니다. 이는 테스트 자체의 기대 실패가 아니며 의존성 환경을 복구해야 합니다.

## 구조

```text
tests/
|- agents/      # Agent 단위·통합
|- llm/         # 모델 클라이언트
|- mcp_bridge/  # MCP 계약과 핸드셰이크
|- rag/         # 임베딩·검색
|- tools/       # 데이터 Tool
`- test_*.py    # 파이프라인·UI 입력·출력 계약
```
