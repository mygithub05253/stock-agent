# `notebooks/` - 탐색·시연 노트북

> Agent 동작과 데이터 비교를 셀 단위로 설명하는 재현 가능한 walkthrough를 보관합니다.

## 현재 파일

`competitor_agent_walkthrough.ipynb`는 Competitor 입력, peer 비교, 결과 해석 흐름을 보여줍니다.

## 사용 기술과 규칙

- Jupyter, Python, 프로젝트 패키지를 사용합니다.
- 핵심 도메인 로직을 노트북에만 구현하지 않습니다.
- 큰 출력, 비밀값, 개인 데이터, 실행 캐시는 커밋하지 않습니다.
- 노트북 결과가 코드와 다르면 `src/stock_agent/`와 테스트를 기준으로 갱신합니다.

```bash
pip install -e .[dev]
jupyter notebook notebooks/competitor_agent_walkthrough.ipynb
```
