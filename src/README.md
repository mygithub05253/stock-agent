# `src/` - 설치 가능한 Python 소스

> `src` 레이아웃으로 애플리케이션 패키지를 테스트·스크립트·Streamlit 진입점과 분리합니다.

## What / Why

- `stock_agent/`가 실제 설치되는 Python 패키지입니다.
- 저장소 루트의 스크립트가 우연히 import되는 문제를 줄입니다.
- `pyproject.toml`의 setuptools package discovery가 이 폴더를 기준으로 합니다.
- editable install 후 `stock_agent.*` 경로로 일관되게 import합니다.
- `stock_agent.egg-info/`는 설치 과정의 생성물이며 직접 수정하지 않습니다.

## 기술 스택

Python 3.11+, setuptools, Pydantic, LangGraph를 사용합니다.

## 사용과 검증

```bash
pip install -e .[dev]
python -c "import stock_agent; print(stock_agent.__file__)"
```

## 구조

```text
src/
`- stock_agent/  # 애플리케이션 패키지
```

세부 구조는 [`stock_agent/README.md`](stock_agent/README.md)를 참고합니다.
