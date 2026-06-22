# `pages/` - Streamlit 멀티페이지 확장 영역

> Streamlit이 루트 `streamlit_app.py` 옆에서 자동 인식하는 페이지 폴더입니다.

## 폴더 소개

- **What:** 향후 독립된 분석·산출물·관리 화면을 추가하는 표준 위치입니다.
- **Why:** Streamlit의 파일 기반 페이지 탐색 규칙을 따르기 위해 루트에 둡니다.
- 현재는 `README.md`와 `.gitkeep`만 있으며 별도 페이지는 구현되지 않았습니다.
- 온보딩, 분석, 결과, 다운로드는 현재 `streamlit_app.py` 한 화면에서 동작합니다.
- 페이지를 추가해도 분석 로직은 `src/stock_agent/graph/pipeline.py`만 호출합니다.

## 기술 스택

Streamlit multipage, `st.session_state`, Pydantic 결과 모델을 사용합니다.

## 동작 원리

파일명 `<순번>_<페이지명>.py`의 순번이 사이드바 순서가 되고 페이지명이 표시명으로 사용됩니다. 재사용 표현은 [`ui/components/`](../ui/components/README.md)로 분리합니다.

## 예정 구조

```text
pages/
|- 1_분석_진행중.py  # Agent 진행 상태
|- 2_추천_결과.py    # Tier 1/2 결과
|- 3_상세_산출물.py  # Tier 3 다운로드
`- 9_관리자_평가.py  # 평가 리포트
```

위 파일은 계획이며 현재 저장소에는 없습니다.

## 검증

페이지 추가 시 `python -m streamlit run streamlit_app.py`로 사이드바 노출과 세션 이동을 확인하고 Streamlit 관련 테스트를 추가합니다.
