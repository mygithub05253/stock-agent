# `scripts/` - 실행·운영 보조 명령

> 애플리케이션 실행, DB 점검, MCP 시연, 통합 흐름 확인을 위한 명시적 진입점 모음입니다.

## 폴더 소개

- **What:** 반복 운영 절차를 한 번의 명령으로 실행합니다.
- **Why:** 팀원이 Python 내부 모듈이나 긴 Docker 명령을 직접 조합하지 않게 합니다.
- 로컬 Streamlit 실행과 포트·환경변수 처리를 제공합니다.
- 기존 DB 볼륨에 스키마를 적용하고 연결 상태를 확인합니다.
- MCP 핸드셰이크와 외부 소비자 예제를 제공합니다.

## 기술 스택

Python, Bash, Docker Compose, PostgreSQL, MCP를 사용합니다.

## 주요 파일

| 파일 | 역할 |
|------|------|
| `run_local_streamlit.sh` | 로컬 Streamlit 실행 |
| `apply_db_schema.py` | 기존 DB 볼륨에 최신 SQL 적용 |
| `check_db.py` | DB·pgvector·RAG 테이블 점검 |
| `run_user_intake_demo.py` | 온보딩·분석 콘솔 데모 |
| `mcp_peer_handshake_demo.py` | MCP 초기화와 tool discovery 시연 |
| `mcp_external_consumer_demo.py` | 외부 소비자 API 예제 |
| `test_curator_integration.py` | Curator 통합 수동 점검 |

## 동작 원리

스크립트는 얇은 진입점으로 유지하며 실제 도메인 로직은 `src/stock_agent/`를 호출합니다. 비밀값은 파일에 넣지 않고 프로세스 환경변수로 주입합니다.

## 검증

```bash
python scripts/check_db.py
python scripts/mcp_peer_handshake_demo.py
scripts/run_local_streamlit.sh
```
