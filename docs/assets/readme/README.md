# `docs/assets/readme/` - 루트 README 시각 자료

> 실제 Streamlit 화면과 GPT Image 2.0으로 만든 프로젝트 썸네일·아키텍처 이미지를 보관합니다.

## 파일

| 파일 | 역할 |
|------|------|
| `current-streamlit-onboarding.png` | 1280x720 첫 온보딩 화면 캡처 |
| `current-streamlit-results.png` | HOLD·신뢰도·적합도 결과 화면 캡처 |
| `stock-agent-thumbnail.png` | 루트 README 대표 썸네일 |
| `stock-agent-architecture.png` | 루트 README 아키텍처 인포그래픽 |

## 생성 방식

- 두 캡처는 2026-06-20 `http://localhost:8501` 실제 실행 화면입니다.
- 두 대표 이미지는 기본 내장 이미지 생성 도구의 GPT Image 2.0 경로로 만들었습니다.
- 썸네일 프롬프트는 실제 Streamlit 캡처를 참고해 navy/blue/teal 핀테크 대시보드와 병렬 Agent 근거 흐름을 요청하고 긴 문장·로고·수익 보장을 금지했습니다.
- 아키텍처 프롬프트는 Mermaid의 데이터 -> PostgreSQL/pgvector -> LangGraph Agent -> Guardrail/Renderer -> Streamlit 흐름과 정확한 짧은 라벨을 요청했습니다.

## 정확성 기준

생성형 아키텍처 이미지는 요약용입니다. 노드·화살표의 정확한 기준은 [`docs/architecture/readme_system_architecture.md`](../../architecture/readme_system_architecture.md)입니다.

[상위 자산 인덱스](../README.md)
