"""
streamlit_app.py — Streamlit Cloud 진입점 (홈 페이지)

이 파일이 Streamlit Cloud의 메인 페이지입니다.
실제 기능 구현은 7주차부터. 현재는 placeholder.

실행:
    streamlit run streamlit_app.py

Streamlit 멀티페이지 자동 인식:
    pages/ 폴더 안의 .py 파일이 자동으로 좌측 사이드바에 노출됩니다.
    파일명 형식: <순번>_<페이지명>.py  (예: 1_분석_진행중.py)
"""

import streamlit as st


def main() -> None:
    st.set_page_config(
        page_title="stock-agent — 투자 의사결정 지원",
        page_icon="📊",
        layout="wide",
    )

    st.title("📊 stock-agent")
    st.caption("BDAI 12기 — 투자자 의사결정 지원 멀티에이전트 시스템")

    st.warning(
        "🚧 현재는 6주차 기획 단계입니다. "
        "실제 기능 구현은 7주차(2026-05-15)부터 시작됩니다."
    )

    st.divider()

    st.markdown(
        """
### 진행 상황 (PM 안내)

- ✅ **6주차 (이번 주)** — PRD v0.6, 기능명세서, 협업 가이드 완성
- ⏳ **7주차** — DB 스키마 적용 + Quant Worker 첫 호출 + Hello E2E
- ○ **8주차** — 기본 기능 5개 완성 + langfuse 연동
- ○ **9주차** — 중간 시연 (박민호 페르소나)
- ○ **10주차** — 고급 기능 시작 (A2A 패턴)
- ○ **11주차** — 고급 기능 완성
- ○ **12주차** — Streamlit Cloud 라이브 배포 + 발표

### 문서 보러가기

- [PRD v0.6](docs/prd/PRD_v0.6.md)
- [기능 명세서](docs/functional-spec/functional_spec_v0.1.md)
- [시스템 흐름도](docs/architecture/system_flow.md)
- [용어집](docs/glossary.md)

---

> 본 시스템 출력은 투자 권유가 아닙니다. (교육용 프로토타입)
        """
    )


if __name__ == "__main__":
    main()
