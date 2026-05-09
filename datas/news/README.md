# News Data

뉴스 데이터 수집 작업 공간입니다.

## 담당 범위

- 국내외 금융 뉴스 수집
- 기사 제목, 본문, 발행 시각, 출처, URL 정리
- 중복 기사 식별 기준 정의
- `raw_news` 테이블 적재

## 권장 파일 구성

```text
datas/news/
├── README.md
└── collector.py
```

수집 API별 파일이 필요해지면 `datas/news/providers/`를 추가해서 분리합니다.
