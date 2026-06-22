# `docs/agents/` - Agent 상세 문서와 시각화

> 코드보다 넓은 Agent별 설계 의도, 데이터 흐름, 발표용 HTML을 보관합니다.

## 이 폴더가 답하는 질문

- Competitor, Qual, Guardrail은 어떤 근거와 폴백을 사용하는가?
- 뉴스 RAG와 Tier 3 다운로드는 어떻게 연결되는가?
- 발표나 리뷰에서 실행 흐름을 어떤 화면으로 설명하는가?

## 형식과 동작

Markdown은 설계 기준, HTML은 브라우저 시연 자료입니다. 구현 사실은 `src/stock_agent/agents/`와 테스트를 우선하며 문서가 다르면 코드를 기준으로 갱신합니다.

## 주요 파일

| 파일 | 내용 |
|------|------|
| `competitor_agent_mvp.md` | Competitor 구현·폴백·회귀 기준 |
| `guardrail.md` | 금융 표현 안전 정책 |
| `tier3_downloads.md` | PDF·Excel·HTML 산출물 |
| `*_flow.html` | 발표용 Agent 흐름 시각화 |

[상위 문서 인덱스](../README.md)
