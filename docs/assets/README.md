# `docs/assets/` - 문서용 시각 자산

> README, 아키텍처, 가이드가 참조하는 SVG·PNG 자산을 보관합니다.

## 사용 기술과 원칙

- SVG는 결정적으로 생성 가능한 구조도에 사용합니다.
- PNG는 실제 UI 캡처나 GPT Image 2.0 생성 자산에 사용합니다.
- 파일명은 사용 위치와 내용을 설명하는 kebab-case를 사용합니다.
- 원본 문서 또는 생성 근거를 같은 문서 트리에 남깁니다.
- 사용자 데이터·API 키·개인정보가 포함된 캡처는 저장하지 않습니다.

## 구조

```text
assets/
|- backtesting_demo_architecture.svg
`- readme/  # 루트 README용 이미지와 실제 UI 캡처
```

- [README 자산](readme/README.md)
- [상위 문서 인덱스](../README.md)
