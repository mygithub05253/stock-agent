# stock-agent

금융 데이터 수집과 분석을 위한 프로젝트입니다. 초기 구성은 PostgreSQL과 Docker Compose를 기준으로 잡았고, 팀원들이 맡는 데이터 수집 영역이 서로 충돌하지 않도록 `datas/` 아래에 데이터 소스별 하위 폴더를 분리했습니다.

## 목표

- 뉴스 데이터 수집 및 정제
- 매크로 지표 수집 및 정제
- DART 기반 종목 분석 데이터 수집 및 정제
- PostgreSQL 저장소를 중심으로 한 공통 데이터 적재
- 이후 분석, 백테스트, 리포트 생성 단계로 확장 가능한 구조 유지

## 프로젝트 구조

```text
.
├── datas/
│   ├── news/              # 뉴스 수집기와 관련 문서
│   ├── macro/             # 매크로 지표 수집기와 관련 문서
│   └── dart/              # DART 종목 분석 데이터 수집기와 관련 문서
├── db/
│   └── init/              # PostgreSQL 초기화 SQL
├── scripts/               # 실행 스크립트
├── src/
│   └── stock_agent/       # 공통 설정, DB 연결 등 애플리케이션 코드
├── tests/                 # 테스트 코드
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## 빠른 시작

### 1. 환경 변수 준비

```bash
cp .env.example .env
```

필요한 값은 `.env`에 채워 넣습니다. API 키는 커밋하지 않습니다.

### 2. PostgreSQL 실행

```bash
docker compose up -d db
```

기본 접속 정보는 다음과 같습니다.

- Host: `localhost`
- Port: `5432`
- Database: `stock_agent`
- User: `stock_agent`
- Password: `stock_agent`

### 3. Python 개발 환경

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 4. DB 연결 확인

```bash
python scripts/check_db.py
```

## 데이터 수집 작업 규칙

각 데이터 수집 담당자는 본인이 맡은 폴더 아래에서 작업합니다.

- 뉴스: `datas/news/`
- 매크로: `datas/macro/`
- DART 종목 분석: `datas/dart/`

공통으로 쓰는 DB 연결, 환경 변수 로딩, 공통 유틸은 `src/stock_agent/`에 둡니다. 여러 수집기에서 같이 필요한 코드만 공통 영역으로 올리고, 소스별 수집 로직은 각 `datas/*` 폴더 안에 유지합니다.

## 데이터 저장 원칙

초기 스키마는 `db/init/001_create_raw_tables.sql`에 있습니다. 수집 원본은 우선 JSONB 형태로 저장해서 원천 데이터 손실을 줄이고, 정제 테이블은 데이터 형태가 안정된 뒤 별도로 추가합니다.

기본 원천 테이블:

- `raw_news`
- `raw_macro`
- `raw_dart`

## Docker 명령어

```bash
docker compose up -d db
docker compose logs -f db
docker compose down
```

앱 컨테이너에서 DB 연결을 확인하려면 다음 명령을 사용합니다.

```bash
docker compose --profile app up --build app
```

DB 볼륨까지 삭제하려면 아래 명령을 사용합니다. 로컬 데이터가 삭제되므로 주의하세요.

```bash
docker compose down -v
```

## Git 협업 가이드

- `.env`, 로컬 DB 파일, 가상환경은 커밋하지 않습니다.
- 데이터 소스별 작업은 가능한 한 `datas/news`, `datas/macro`, `datas/dart` 안에서 진행합니다.
- 공통 코드 변경이 필요하면 PR 또는 커밋 메시지에 어떤 수집기와 연관되는지 적습니다.
