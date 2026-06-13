# `eval/` — 평가 하네스 (Evaluation Harness)

부트캠프 W2 학습 적용 영역. 시스템 신뢰성을 **정량 지표**로 측정합니다.

## 파일 (실제 구현 상태)

```
eval/
├── golden_set/
│   ├── personas.json              ✅ 페르소나 5개 케이스 (질문 + 투자성향 + 포트폴리오)
│   └── expected_outputs.json      ✅ 케이스별 기대 결과 (intent·urgency·종목·공통 계약)
├── reports/
│   └── YYYY-MM-DD_benchmark.md    ✅ 실행 시 자동 생성 (md + json 쌍)
└── run_benchmark.py               ✅ 한 명령으로 전체 평가 실행
```

## 측정 지표

| 지표 | 측정 방법 | LLM 비용 | 목표 |
|------|----------|---------|------|
| Rule-based 계약 준수 | 신호 유효성·면책 문구·confidence/suitability 범위·근거 존재·intent/urgency 분류 일치 | 0원 | 100% |
| RAGAS Faithfulness | LLM-as-judge (OpenRouter) — 답변이 worker 근거(contexts)에 충실한지 | 소액 | ≥ 0.80 |
| RAGAS Answer Relevancy | judge + 로컬 bge-m3 임베딩 (`--with-relevancy`) | 소액 | ≥ 0.70 |

## 실행

```bash
pip install -e .[eval]                        # 최초 1회

python eval/run_benchmark.py                  # 전체 5케이스 + faithfulness
python eval/run_benchmark.py --skip-ragas     # LLM 비용 0원 (rule-based만)
python eval/run_benchmark.py --limit 2        # 케이스 수 제한 (크레딧 절약)
python eval/run_benchmark.py --case park_minho_hold_review
python eval/run_benchmark.py --with-relevancy # answer_relevancy 추가
```

## 비용 정책 (중요)

- RAGAS judge는 `OPENROUTER_API_KEY` 가 설정된 경우에만 호출됩니다. 키가 없으면 rule-based만 수행하고 정상 종료합니다.
- judge 모델은 `OPENROUTER_MODEL` 설정을 따릅니다 (기본: 저비용 flash 계열).
- 임베딩은 비용이 들지 않는 로컬 bge-m3 (Qual RAG와 동일 모델)를 사용합니다.
- **팀 OpenRouter 크레딧이 한정되어 있으니 전체 케이스 + relevancy 실행은 하루 1회 이내를 권장합니다.**

## 골든셋 확장 규칙

- `personas.json` 의 `cases[]` 에 케이스를 추가하고, 같은 `case_id` 로 `expected_outputs.json` 에 기대값을 추가합니다.
- 기대값에 넣을 수 있는 키: `expected_stock_code`, `expected_intent`, `expected_urgency`, `expect_candidates`
- 케이스는 실제 사용자 시나리오(보유 점검·추가 매수·손절·공시 확인·포트폴리오 리뷰)를 대표해야 합니다.
