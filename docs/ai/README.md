# `docs/ai/` — AI 시스템 설계·평가 문서

> stock-agent의 모델·프롬프트·오케스트레이션·평가를 코드 기준으로 문서화한 영역입니다.

## 한 줄 소개
LLM·임베딩 선택과 11노드 오케스트레이션, 프롬프트 계약, 평가 결과를 한곳에 모은 AI 문서 세트.

## 소개
- **What:** 모델 카드 / 프롬프트 명세 / 평가 보고서 / 오케스트레이션 설계 + 발표용 요약본.
- **Why:** 강사 채점(성숙도·평가) 대응과 포트폴리오·면접 설명을 동시에 만족시키기 위해.
- 모든 수치·라우팅은 코드(`config.py`·`agents`·`graph/pipeline.py`)와 `eval/reports/`에서 직접 추출.

## 기술 스택
LangGraph `StateGraph`/`Send`, OpenRouter Qwen2.5-7B, Z.ai GLM-4.5-flash, BGE-M3(pgvector 1024-dim), RAGAS·rule-based 평가.

## 동작 원리
`config.py` 모델 설정 → Agent별 `prompts/*/system.md` 계약 → 11노드 그래프 실행 → `eval/run_*`로 회귀. 본 문서들은 그 산출물을 사람이 읽는 형태로 승격합니다.

## 구조
```text
docs/ai/
|- model_card.md          모델 선택·역할·한계·비용·라이선스 (config.py 기준)
|- prompt_spec.md         6개 프롬프트 입출력 계약 (system.md 기준)
|- eval_report.md         RAGAS·rule·Competitor·RAG 검색 결과 서사 (eval/reports 기준)
|- orchestration.md       Send fan-out·join·revision loop 설계 근거 (pipeline.py 기준)
`- ai_summary_1pager.md   발표·면접용 1~2장 요약본
```

## 성과·상태
- 풀세트 4종 + 요약본 1종 작성 완료 (2026-06-20).
- 핵심 개선 과제: RAG faithfulness 0.41 → 0.80 ([eval_report.md](eval_report.md) §2.1).

## 기준 문서
- SSOT: [`docs/architecture/pipeline_11node_groundtruth.md`](../architecture/pipeline_11node_groundtruth.md)
- 인터페이스: [`docs/interface/interface_spec.md`](../interface/interface_spec.md)
