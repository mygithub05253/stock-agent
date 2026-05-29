from typing import Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

def get_financial_metrics(conn, corp_code: str, as_of_date: str) -> Dict[str, Optional[float]]:
    """
    [financial_tool] 기준일 이전 최신 재무제표를 바탕으로 ROE, 영업이익률, 매출성장률, 부채비율을 계산합니다.
    """
    query = """
        WITH latest_report AS (
            SELECT bsns_year, reprt_code 
            FROM financial_statement
            WHERE corp_code = %s AND bsns_year <= EXTRACT(YEAR FROM CAST(%s AS DATE))
            ORDER BY 
                bsns_year DESC,
                CASE reprt_code
                    WHEN '11011' THEN 4
                    WHEN '11014' THEN 3
                    WHEN '11012' THEN 2
                    WHEN '11013' THEN 1
                    ELSE 0
                END DESC
            LIMIT 1
        )
        SELECT account_nm, amount, bsns_year, reprt_code
        FROM financial_statement
        WHERE corp_code = %s 
          AND bsns_year = (SELECT bsns_year FROM latest_report)
          AND reprt_code = (SELECT reprt_code FROM latest_report);
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, (corp_code, as_of_date, corp_code))
        rows = cur.fetchall()

    fs_map = {r["account_nm"]: r["amount"] for r in rows}
    
    total_assets = fs_map.get("자산총계", 0)
    total_liabilities = fs_map.get("부채총계", 0)
    total_equity = fs_map.get("자본총계", 0)
    net_income = fs_map.get("당기순이익", 0)
    operating_income = fs_map.get("영업이익", 0)
    current_revenue = fs_map.get("매출액", 0)

    roe = round((net_income / total_equity) * 100, 2) if total_equity and total_equity > 0 else None
    operating_margin = round((operating_income / current_revenue) * 100, 2) if current_revenue and current_revenue > 0 else None
    debt_ratio = round((total_liabilities / total_equity) * 100, 2) if total_equity and total_equity > 0 else None

    revenue_growth = None
    if rows:
        fetched_year = rows[0]["bsns_year"]
        fetched_code = rows[0]["reprt_code"]
        prev_query = """
            SELECT amount FROM financial_statement 
            WHERE corp_code = %s AND bsns_year = %s AND reprt_code = %s AND account_nm = '매출액' LIMIT 1;
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(prev_query, (corp_code, fetched_year - 1, fetched_code))
            prev_row = cur.fetchone()
            if prev_row and prev_row["amount"] > 0:
                revenue_growth = round(((current_revenue - prev_row["amount"]) / prev_row["amount"]) * 100, 2)

    return {
        "roe": roe,
        "operating_margin": operating_margin,
        "revenue_growth_yoy": revenue_growth,
        "debt_ratio": debt_ratio
    }