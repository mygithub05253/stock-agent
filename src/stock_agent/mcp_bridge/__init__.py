"""MCP 데이터 브리지 패키지.

Competitor Agent가 DB에 연결하지 못했을 때, 하드코딩 mock 대신 자체 MCP 서버
(`peer_data_server`)를 in-process로 띄워 pykrx 실시간 시세 기반 peer 비교를 확보한다.
이로써 루브릭 #6(MCP/A2A)의 "외부 데이터 Tool 1개를 MCP 서버로 노출 + 실동작 1경로"를
충족한다.

- `peer_roster`   : 섹터별 비교군 로스터(번들 정적 데이터, 외부 의존 없음)
- `peer_data_server`: FastMCP 서버. pykrx로 시세/밸류에이션 지표를 조회해 Tool로 노출
- `peer_data_client`: stdio MCP 클라이언트. Competitor 폴백에서 동기 래퍼로 호출

`mcp`/`pykrx`가 설치되지 않은 환경에서는 server/client 모듈이 graceful하게 비활성화되어
(import 자체는 성공하되 호출 시 사용 불가 신호 반환) DB 정상 경로와 테스트에는 영향이 없다.
설치: `pip install -e .[mcp]`
"""
