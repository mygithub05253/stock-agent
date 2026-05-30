# `src/stock_agent/llm/` — LLM 추상화 + 비용 라우팅

## 핵심 원칙

> **모든 LLM 호출은 반드시 본 모듈을 거친다.** 직접 `openai.ChatCompletion.create()` 호출 금지.

이유는 두 가지:
1. **모델 라우팅** — 작업 난이도에 따라 작은/큰 모델 자동 선택 → 비용 절감
2. **비용 추적** — 모든 호출의 입출력 토큰·비용을 LangSmith + DB에 기록

## 파일

| 파일 | 역할 |
|------|------|
| `factory.py` | `get_llm(task_type)` 팩토리 함수. task_type 으로 모델 자동 선택 |
| `glm_client.py` | GLM OpenAI-compatible chat/completions 호출 adapter |
| `routing.py` | task_type → 모델 매핑 정책 (예: parsing → gpt-4o-mini, decision → solar) |
| `tracker.py` | LangSmith 트레이싱 + 비용 추적 |

## 모델 정책 (자세히는 `docs/operations/llm_cost_guide.md`)

| Task Type | Primary | Fallback | 1회 비용 |
|-----------|---------|----------|----------|
| `parsing` (의도 파싱·구조화) | gpt-4o-mini | Solar | ~10원 |
| `rag_summary` (RAG 요약) | Solar | gpt-4o-mini | 0원 |
| `decision` (최종 매수/매도) | gpt-4o | Solar | ~50원 |
| `guardrail` (필터·검증) | gpt-4o-mini | rule-based | ~5원 |

## 로컬 GLM 설정

`.env`에는 키를 커밋하지 않습니다. 로컬 실행 시 프로세스 환경변수로만 주입합니다.

```bash
GLM_API_KEY=... \
GLM_BASE_URL=https://api.z.ai/api/paas/v4 \
GLM_MODEL=glm-4.5-flash \
streamlit run streamlit_app.py
```
