import os
import io
import time
import zipfile
import requests
import psycopg2
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# RAG용 공시 원문 텍스트 수집
# collector.py가 가져온 3개년 공시 목록 중 본문이 비어 있는 대상을 추려 원문을 파싱합니다.

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
DART_API_KEY = os.getenv("DART_API_KEY")

def collect_disclosure_contents():
    print("4탄: RAG용 공시 원문 텍스트 데이터 수집 시작...")
    
    if not DART_API_KEY:
        print("DART_API_KEY 누락")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT dr.rcept_no, dr.report_nm 
            FROM disclosure_report dr
            LEFT JOIN disclosure_content dc ON dr.rcept_no = dc.rcept_no
            WHERE dc.rcept_no IS NULL;
        """)
        target_reports = cursor.fetchall()
        
        if not target_reports:
            print("이미 모든 공시 보고서의 원문 텍스트가 수집되어 있습니다.")
            return
            
        print(f"본문 수집 대상 보고서: {len(target_reports)}건")
        
    except Exception as e:
        print(f"DB 조회 실패: {e}")
        return

    url = "https://opendart.fss.or.kr/api/document.xml"
    insert_query = """
        INSERT INTO disclosure_content (rcept_no, content, summary)
        VALUES (%s, %s, %s)
        ON CONFLICT (rcept_no) 
        DO UPDATE SET 
            content = EXCLUDED.content,
            updated_at = NOW();
    """

    success_count = 0

    try:
        for rcept_no, report_nm in target_reports:
            print(f"📄 [{report_nm}] ({rcept_no}) 원문 다운로드 중...")
            
            params = {"crtfc_key": DART_API_KEY, "rcept_no": rcept_no}
            time.sleep(0.5)
            
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
            except Exception as e:
                print(f"API 연결 오류 패스: {e}")
                continue

            if not zipfile.is_zipfile(io.BytesIO(response.content)):
                try:
                    err_soup = BeautifulSoup(response.content, "lxml-xml")
                    err_msg = err_soup.find("message").text if err_soup.find("message") else "알 수 없는 API 에러"
                    print(f"OpenDART API 거부: {err_msg}")
                except:
                    print("올바른 ZIP 파일 포맷이 아닙니다.")
                continue

            try:
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    file_list = z.namelist()
                    if not file_list:
                        continue
                    
                    raw_xml = z.read(file_list[0])
                    soup = BeautifulSoup(raw_xml, "lxml-xml")
                    clean_text = soup.get_text("\n", strip=True)
                    
                    if not clean_text.strip():
                        continue
                    
                    cursor.execute(insert_query, (rcept_no, clean_text, None))
                    conn.commit()
                    success_count += 1
                    
            except Exception as e:
                conn.rollback()
                print(f"본문 파싱 또는 DB 적재 에러 패스: {e}")
                continue
                
        print(f"성공: 총 {success_count}건의 공시 원문 텍스트 데이터가 최종 적재되었습니다.")
        
    except Exception as e:
        print(f"치명적 오류 발생: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    collect_disclosure_contents()