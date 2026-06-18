"""peer 비교용 실데이터를 MCP Tool로 노출하는 FastMCP 서버.

`python -m stock_agent.mcp_bridge.peer_data_server` 로 stdio 서버를 띄운다.
노출 Tool:
  - `get_sector_roster(sector)`            : 섹터 비교군 후보(번들 로스터)
  - `get_market_metrics(stock_codes, base_date)` : pykrx 실시간 시세·밸류에이션 지표

설계 메모:
  - pykrx 호출은 `_fetch_market_snapshot`에 격리하고, 순수 매핑 헬퍼(`build_metric_record`,
    `metrics_from_frames`)는 외부 의존 없이 단위 테스트할 수 있게 분리한다.
  - `mcp`/`pykrx` 미설치 시에도 이 모듈의 순수 헬퍼는 import·사용 가능하다(서버 실행만 불가).
"""

from __future__ import annotations

from typing import Any

from stock_agent.mcp_bridge.peer_roster import get_sector_roster as _roster_for_sector


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


def _positive_or_none(value: Any) -> float | None:
    """0 이하·결측은 None으로 정규화(PER 0, PBR 0 등은 결측 신호)."""
    result = _to_float(value)
    if result is None or result <= 0:
        return None
    return result


def _to_int(value: Any) -> int | None:
    result = _to_float(value)
    if result is None:
        return None
    return int(result)


def build_metric_record(
    stock_code: str,
    corp_name: str,
    base_date: str,
    cap_row: dict[str, Any],
    fund_row: dict[str, Any],
) -> dict[str, Any]:
    """pykrx 시가총액 행 + 밸류에이션 행을 peer 비교용 지표 dict로 변환한다(순수 함수).

    cap_row 컬럼: 종가, 시가총액 / fund_row 컬럼: PER, PBR, EPS, BPS
    ROE는 pykrx가 직접 주지 않으므로 EPS/BPS로 근사한다(둘 다 양수일 때만).
    """
    per = _positive_or_none(fund_row.get("PER"))
    pbr = _positive_or_none(fund_row.get("PBR"))
    eps = _to_float(fund_row.get("EPS"))
    bps = _to_float(fund_row.get("BPS"))
    roe: float | None = None
    if eps is not None and bps not in (None, 0):
        roe = round(eps / bps, 4)

    return {
        "stock_code": stock_code,
        "corp_name": corp_name,
        "base_date": base_date,
        "close_price": _to_int(cap_row.get("종가")),
        "market_cap": _to_int(cap_row.get("시가총액")),
        "per": per,
        "pbr": pbr,
        "roe": roe,
        "eps": eps,
        "bps": bps,
    }


def metrics_from_frames(
    stock_codes: list[str],
    base_date: str,
    cap_by_ticker: dict[str, dict[str, Any]],
    fund_by_ticker: dict[str, dict[str, Any]],
    names: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """티커별 시가총액/밸류에이션 매핑에서 요청 종목들의 지표 레코드를 만든다(순수 함수)."""
    names = names or {}
    records: list[dict[str, Any]] = []
    for code in stock_codes:
        records.append(
            build_metric_record(
                stock_code=code,
                corp_name=names.get(code, code),
                base_date=base_date,
                cap_row=cap_by_ticker.get(code, {}),
                fund_row=fund_by_ticker.get(code, {}),
            )
        )
    return records


def _fetch_market_snapshot(stock_codes: list[str], base_date: str | None) -> list[dict[str, Any]]:
    """pykrx로 전체 시장 스냅샷을 받아 요청 종목 지표를 만든다(네트워크 호출).

    pykrx 미설치·조회 실패 시 RuntimeError를 발생시킨다(상위에서 폴백 처리).
    """
    try:
        from pykrx import stock
    except ModuleNotFoundError as exc:  # pragma: no cover - 환경 의존
        raise RuntimeError("pykrx is required to fetch market metrics.") from exc

    date = base_date or stock.get_nearest_business_day_in_a_week()

    def _whole_market(getter) -> dict[str, dict[str, Any]]:
        try:
            frame = getter(date, market="ALL")
        except TypeError:
            # 구버전 pykrx: market 인자 미지원 → KOSPI/KOSDAQ 병합
            frame = getter(date)
            try:
                frame = frame.append(getter(date, market="KOSDAQ"))  # type: ignore[attr-defined]
            except Exception:
                pass
        return {str(ticker): row for ticker, row in frame.to_dict("index").items()}

    cap_by_ticker = _whole_market(stock.get_market_cap_by_ticker)
    fund_by_ticker = _whole_market(stock.get_market_fundamental_by_ticker)

    names: dict[str, str] = {}
    for code in stock_codes:
        try:
            names[code] = stock.get_market_ticker_name(code) or code
        except Exception:
            names[code] = code

    return metrics_from_frames(stock_codes, str(date), cap_by_ticker, fund_by_ticker, names)


# ----- 평범한 함수형 Tool 구현(테스트·재사용 용) -----

def get_sector_roster(sector: str) -> list[dict[str, str]]:
    return _roster_for_sector(sector)


def get_market_metrics(stock_codes: list[str], base_date: str = "") -> list[dict[str, Any]]:
    return _fetch_market_snapshot(stock_codes, base_date or None)


def build_server():  # pragma: no cover - 서버 실행 경로
    """FastMCP 서버 인스턴스를 만들어 Tool을 등록한다. `mcp` 미설치 시 RuntimeError."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError as exc:
        raise RuntimeError("mcp package is required to run the peer data MCP server.") from exc

    server = FastMCP("stock-agent-peer-data")

    @server.tool()
    def sector_roster(sector: str) -> list[dict[str, str]]:
        """섹터 비교군 후보(stock_code/corp_name)를 반환한다."""
        return get_sector_roster(sector)

    @server.tool()
    def market_metrics(stock_codes: list[str], base_date: str = "") -> list[dict[str, Any]]:
        """종목 코드 목록의 실시간 시세·밸류에이션 지표(PER/PBR/ROE/시총)를 반환한다."""
        return get_market_metrics(stock_codes, base_date)

    return server


def main() -> None:  # pragma: no cover - 서버 실행 경로
    build_server().run()


if __name__ == "__main__":  # pragma: no cover
    main()
