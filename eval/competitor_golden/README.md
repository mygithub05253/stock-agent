# `eval/competitor_golden/` - Competitor 회귀 골든셋

> peer 선정 순서, 상대 점수, 데이터 품질 flag를 DB·LLM 없이 재현하는 6개 결정적 시나리오입니다.

## 동작 원리

`cases.json`의 입력 market rows를 `peer_tool` 순수 계산 엔진에 전달하고 실제 결과를 expected snapshot과 비교합니다.

## 검증 범위

- 정상 peer 3개 선정
- 시가총액 band 제외와 peer 부족
- PER outlier flag
- 비교군 없음
- 저품질 타깃 점수 상한
- 복합 유사도 정렬

```bash
python eval/run_competitor_eval.py
```

최신 결과는 **6/6**이며 상세는 [`../reports/2026-06-14_competitor_eval.md`](../reports/2026-06-14_competitor_eval.md)입니다.

[평가 인덱스](../README.md)
