# DART Data

DART 기반 종목 분석 데이터 수집 작업 공간입니다.

## 담당 범위

- 기업 코드, 종목 코드, 공시 보고서 수집
- 재무제표, 주요 공시, 사업보고서 분석에 필요한 원천 데이터 정리
- `raw_dart` 테이블 적재

## 권장 파일 구성

```text
datas/dart/
├── README.md
└── collector.py
```

DART API 종류별로 파일이 커지면 `datas/dart/providers/` 또는 `datas/dart/parsers/`를 추가해서 분리합니다.
