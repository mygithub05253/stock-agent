# `pages/` — Streamlit 멀티페이지

> ⚠️ **이 폴더는 반드시 루트(streamlit_app.py 옆)에 있어야 Streamlit이 자동 인식합니다.**
> `ui/pages/` 같은 곳에 두면 자동 인식 안 됨.

## 파일 명명 규칙

`<순번>_<페이지명>.py` 형식 — Streamlit이 *순번 → 페이지 순서*, *페이지명 → 사이드바 표시명* 으로 사용합니다.

## 예정 페이지 (7~8주차 작성)

```
pages/
├── 1_분석_진행중.py        ← 에이전트 진행 상태 + Thought 토글 (W4 학습)
├── 2_추천_결과.py          ← Tier 1 한 줄 + Tier 2 5개 카드
├── 3_상세_산출물.py        ← Tier 3 다운로드 (Excel·HTML·PDF·DOCX)
└── 9_관리자_평가.py        ← RAGAS·골든셋·langfuse 링크
```

## 작성 규칙

- **비즈니스 로직 직접 호출 금지** — 반드시 `src/stock_agent/graph/pipeline.py` 만 거치기
- **세션 상태**: `st.session_state` 만 사용 (외부 상태 저장 X — Postgres에 영구 저장)
- **재사용 컴포넌트**: `ui/components/` 의 함수 import해 사용

## 진입점

루트 `streamlit_app.py` 가 홈(0번 페이지) 역할. 본 폴더의 페이지들은 사이드바에 자동 노출됨.
