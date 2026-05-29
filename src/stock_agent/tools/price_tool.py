from typing import Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

def get_price_metrics(conn, stock_code: str, as_of_date: str) -> Dict[str, Optional[float]]:
    """
    [price_tool] 지정된 기준일 이전 최신 시세 및 KRX 지표를 반환합니다.
    """
    query = """
        SELECT close_price, volume, market_cap, per, pbr
        FROM stock_price
        WHERE stock_code = %s AND base_date <= %s
        ORDER BY base_date DESC
        LIMIT 1;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, (stock_code, as_of_date))
        row = cur.fetchone()
        
    if not row:
        raise ValueError(f"{as_of_date} 기준 {stock_code}의 시세 데이터가 없습니다.")

    return {
        "close_price": float(row["close_price"]) if row.get("close_price") is not None else None,
        "volume": float(row["volume"]) if row.get("volume") is not None else None,
        "market_cap": float(row["market_cap"]) if row.get("market_cap") is not None else None,
        "per": float(row["per"]) if row.get("per") is not None else None,
        "pbr": float(row["pbr"]) if row.get("pbr") is not None else None,
    }