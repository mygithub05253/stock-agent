# `ui/` — 재사용 UI 컴포넌트만 보관

> ⚠️ **Streamlit 페이지 자체는 루트 `pages/` 에 있습니다** (Streamlit이 자동 인식).
> 본 `ui/` 폴더는 *페이지에서 import 해서 쓰는 재사용 컴포넌트* 만 둡니다.

## 파일

```
ui/
└── components/
    ├── action_card.py             ← BUY/HOLD/SELL 한 줄 결정 컴포넌트 (Tier 1)
    ├── reasoning_card.py          ← 5개 차원 근거 카드 (Tier 2)
    ├── progress_sidebar.py        ← Stage별 ✓/⏳/○ 진행 사이드바
    └── disclaimer.py              ← 책임 고지 푸터 (모든 페이지 공통)
```

## 사용 예시

```python
# pages/2_추천_결과.py 안에서
from ui.components.action_card import render_action_card
from ui.components.reasoning_card import render_5_cards

render_action_card(action="BUY", confidence=0.78, fit=4)
render_5_cards(quant=..., qual=..., comp=..., macro=..., portfolio=...)
```

## 작업 규칙

- 컴포넌트는 **순수 함수** — 입력 받아 `st.write/markdown/...` 호출
- 비즈니스 로직 호출 금지 (페이지에서 graph 호출 후 결과만 컴포넌트로 전달)
- 한글 폰트 깨짐 방지: 차트는 `matplotlib` + `Pretendard` 폰트 임베드
