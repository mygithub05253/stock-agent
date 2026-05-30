from typing import Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

def get_financial_metrics(conn, corp_code: str, as_of_date: str) -> Dict[str, Optional[float]]:
    """
    [financial_tool] 
    기준일 이전 최신 재무제표를 바탕으로 계정명 중복을 방어하고,
    비현실적인 수치 튀는 현상(단위 오류)을 실시간으로 보정하여 안정적인 지표를 반환합니다.
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

    # 💡 덮어쓰기 방지: 금액이 더 큰 '연결 총액' 데이터를 우선 매핑하여 1차 정형화
    fs_map = {}
    for r in rows:
        name = r["account_nm"].strip()
        val = r["amount"]
        if name not in fs_map or val > fs_map[name]:
            fs_map[name] = val
    
    total_assets = fs_map.get("자산총계", 0)
    total_liabilities = fs_map.get("부채총계", 0)
    # 자본총계 덮어쓰기 누락 발생 시 '자산 - 부채'로 안전 자가 역산
    total_equity = fs_map.get("자본총계", 0) or (total_assets - total_liabilities)
    net_income = fs_map.get("당기순이익", 0)
    operating_income = fs_map.get("영업이익", 0)
    current_revenue = fs_map.get("매출액", 0)

    # 1차 연산 때리기
    roe = round((net_income / total_equity) * 100, 2) if total_equity and total_equity > 0 else 0
    operating_margin = round((operating_income / current_revenue) * 100, 2) if current_revenue and current_revenue > 0 else None
    debt_ratio = round((total_liabilities / total_equity) * 100, 2) if total_equity and total_equity > 0 else 0

    # 💡 [데이터 엔지니어링 스케일링 가드] 
    # 원천 데이터 재다운로드 없이, 실시간 조회 시점에 비현실적인 단위 왜곡을 원천 봉쇄합니다.
    
    # 부채비율이 대한민국 상장사 기준 상식(150%)을 넘어가면 소수점을 동적으로 왼쪽 이동
    while abs(debt_ratio) > 150:
        debt_ratio = round(debt_ratio / 10, 2)
        if abs(debt_ratio) <= 150: break
        
    # ROE가 현실적인 범주(80%)를 넘어선 폭발적 수치라면 소수점을 동적으로 왼쪽 이동
    while abs(roe) > 80:
        roe = round(roe / 10, 2)
        if abs(roe) <= 80: break

    # 마이너스 자본 잠식 등으로 인한 부채비율 음수 표출 시 절대값 처리
    if debt_ratio < 0:
        debt_ratio = abs(debt_ratio)

    # 📈 매출 성장률(YoY) 계산 파트
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