# `eval/` — 평가 하네스 (Evaluation Harness)

부트캠프 W2 학습 적용 영역. 시스템 신뢰성을 *정량 지표* 로 측정합니다.

## 파일

```
eval/
├── golden_set/
│   ├── personas.json              ← 박민호·이지영·김재현 페르소나 입력 30~50개
│   └── expected_outputs.json     ← 기대 결과 (Tool 시퀀스, 액션 등)
├── reports/
│   └── YYYYMMDD.md                ← 일별 자동 평가 리포트
└── run_benchmark.py               ← 한 명령으로 전체 평가 실행
```

## 5종 측정 지표

| 지표 | 측정 방법 | 목표 |
|------|----------|------|
| RAGAS Faithfulness | LLM-as-judge 자동 채점 | ≥ 0.80 |
| Action Consistency | 같은 입력 N=5회 호출 → 분포 일치율 | ≥ 80% |
| Tool 호출 정확성 | 골든셋 시퀀스 매칭률 | ≥ 85% |
| Tier 1↔2↔3 정합성 | 한 줄·5카드·7쪽 결론 일치율 | ≥ 90% |
| Guardrail 차단 정확도 | 위험 표현 차단 골든셋 | 100% |

## 실행

```bash
python eval/run_benchmark.py --persona park_minho --n 5
```
