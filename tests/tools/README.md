# `tests/tools/` - 데이터 Tool 검증

> Agent가 사용하는 조회·비교 Tool의 결정적 계산 규칙을 검증합니다.

## 범위

- 현재는 `peer_tool.py`의 peer 선정과 상대 비교를 집중 검증합니다.
- 시장가치 band, 데이터 품질, outlier, 정렬 기준을 확인합니다.
- DB나 LLM 없이 순수 입력 데이터로 실행합니다.
- 상위 Competitor 회귀는 `eval/run_competitor_eval.py`가 담당합니다.
- Tool이 반환하는 warning과 품질 flag도 계약에 포함합니다.

## 실행

```bash
python -m pytest tests/tools -v
```

## 구조

```text
tools/
`- test_peer_tool.py
```
