# `eval/reports/` - 평가 결과 스냅샷

> 평가 실행 결과를 사람이 읽는 Markdown과 자동화가 읽는 JSON 쌍으로 보관합니다.

## 현재 결과

| 날짜 | 평가 | 핵심 결과 |
|------|------|-----------|
| 2026-06-12 | Phase 1 benchmark | rule **40/41**, faithfulness **0.4096** |
| 2026-06-14 | Competitor regression | **6/6** |
| 2026-06-20 | Competitor regression 재검증 | **6/6** |

## 생성 원리

`eval/run_benchmark.py`와 `eval/run_competitor_eval.py`가 같은 날짜·stem의 `.md`와 `.json`을 만듭니다. 결과를 손으로 고치지 않고 입력·평가 코드를 수정한 뒤 다시 생성합니다.

[평가 인덱스](../README.md)
