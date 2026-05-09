# Macro Data

매크로 지표 수집 작업 공간입니다.

## 담당 범위

- 금리, 환율, 물가, 고용, 성장률 등 거시경제 지표 수집
- 지표 코드와 관측일 기준 정리
- `raw_macro` 테이블 적재

## 권장 파일 구성

```text
datas/macro/
├── README.md
└── collector.py
```

FRED, 한국은행 ECOS 등 공급자가 늘어나면 `datas/macro/providers/`를 추가해서 분리합니다.
