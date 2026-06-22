# `tests/llm/` - LLM 클라이언트 검증

> 외부 모델 응답 파싱, 오류 처리, smoke 경로가 도메인 로직과 분리되어 있는지 확인합니다.

## 범위와 기술

- pytest와 monkeypatch로 OpenRouter HTTP 응답을 대체합니다.
- 정상 JSON, 오류 응답, API 키 누락과 fallback을 검증합니다.
- 실제 호출은 `openrouter_smoke` marker와 로컬 환경변수가 있을 때만 실행합니다.
- 비밀값은 fixture나 저장소에 기록하지 않습니다.
- Agent 결과 품질 평가는 `eval/`이 담당합니다.

## 실행

```bash
python -m pytest tests/llm -v
python -m pytest -m openrouter_smoke -v
```

## 구조

```text
llm/
`- test_openrouter_client.py
```
