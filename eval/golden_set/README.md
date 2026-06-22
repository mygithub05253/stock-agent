# `eval/golden_set/` — 평가용 골든셋

`run_benchmark.py`가 사용하는 페르소나 입력과 기대 결과입니다.

## 폴더 소개

- **What:** 5개 대표 사용자 질문, 성향, 포트폴리오와 기대 분류를 저장합니다.
- **Why:** 코드 변경 전후의 신호·면책·intent·urgency 계약을 같은 입력으로 비교합니다.
- 입력은 `personas.json`, 기대 계약은 `expected_outputs.json`으로 분리합니다.
- JSON은 pytest와 평가 스크립트가 함께 소비합니다.
- 골든셋 변경은 기준 완화가 아닌 실제 사용자 시나리오 확장으로 리뷰합니다.

## 기술과 동작

JSON -> `eval/run_benchmark.py` -> 실제 LangGraph pipeline -> rule-based/RAGAS 평가 순서입니다. 최신 5개 케이스는 규칙 기반 항목 **40/41**을 통과했습니다.

| 파일 | 내용 |
|------|------|
| `personas.json` | 5개 페르소나 케이스 — `case_id·persona·query·user_profile·portfolio` |
| `expected_outputs.json` | rule-based 채점 기대값(신호 유효성·의도 분류 등) |

## RAGAS 지표와 필요한 필드

| 지표 | 필요 데이터 | 현재 상태 |
|------|-------------|-----------|
| faithfulness | question·answer·contexts | ✅ 동작 (기본) |
| answer_relevancy | + 임베딩(로컬 bge-m3) | ✅ `--with-relevancy` |
| **context_precision** | question·contexts·answer (**reference 불필요**) | ✅ `--with-contexts` |
| **context_recall** | + **reference(정답)** | ⏳ 아래 절차로 reference 채운 뒤 추가 |

## context_recall 활성화 절차 (팀 작성 필요)

context_recall은 "정답 대비 검색 컨텍스트가 얼마나 회수됐는가"를 보므로 **케이스별 정답(reference)** 이 필요합니다. 정답은 **도메인 지식 기반으로 팀이 직접 작성·검증**해야 합니다(임의 생성 금지 — 평가 신뢰도 훼손).

1. `personas.json`의 각 케이스에 `reference` 필드를 추가합니다.

   ```json
   {
     "case_id": "case_01",
     "persona": "...",
     "query": "삼성전자 지금 사도 될까?",
     "user_profile": { ... },
     "portfolio": { ... },
     "reference": "삼성전자는 ... (해당 질문에 대해 데이터로 뒷받침되는 모범 답안 1~3문장)"
   }
   ```

2. `run_benchmark.py`의 `run_ragas`에서 context_precision 옆에 동일 패턴으로 추가합니다.

   ```python
   from ragas.metrics import LLMContextRecall
   # dataset 항목에 "reference": r.reference 추가 필요
   metrics.append(LLMContextRecall(llm=judge))
   ```

3. `CaseRecord`와 `EvaluationDataset.from_list(...)`에 `reference`를 전달하도록 연결합니다.

4. 채워진 DB + `OPENROUTER_API_KEY`로 재측정해 `eval/reports/`에 리포트를 커밋합니다.

> **측정 요건**: 모든 RAGAS 지표는 `OPENROUTER_API_KEY`(judge)가 있어야 실행됩니다. 키가 없으면 `run_ragas`가 `None`을 반환하고 rule-based 채점만 남깁니다(크래시 없음).
