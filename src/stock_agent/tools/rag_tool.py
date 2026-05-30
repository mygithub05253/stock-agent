from typing import Any, Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor

def get_disclosure_context(conn, corp_code: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    [rag_tool] 지정된 기간 동안 Supabase에 적재된 공시 보고서 원문을 날짜순으로 긁어모읍니다.
    """
    query = """
        SELECT dr.report_nm, dr.rcept_dt, dc.content
        FROM disclosure_report dr
        JOIN disclosure_content dc ON dr.rcept_no = dc.rcept_no
        WHERE dr.corp_code = %s 
          AND dr.rcept_dt >= %s 
          AND dr.rcept_dt <= %s
        ORDER BY dr.rcept_dt ASC;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, (corp_code, start_date, end_date))
        rows = cur.fetchall()
        
    return [dict(row) for row in rows]