import os
import io
import time
import zipfile
import requests
import psycopg2
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
DART_API_KEY = os.getenv("DART_API_KEY")

def collect_disclosure_contents():
    print("RAG용 공시 원문 텍스트 데이터 수집 시작...")
    
    if not DART_API_KEY:
        print("에러: .env 파일에 DART_API_KEY가 설정되지 않았습니다.")
        return

    # 1. DB에서 목차는 있지만 본문(content)이 아직 수집되지 않은 rcept_no 조회
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
            print("이미 모든 공시 보고서의 원문 텍스트가 수집되어 있습니다!")
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
            print(f"[{report_nm}] ({rcept_no}) 원문 다운로드 중...")
            
            params = {
                "crtfc_key": DART_API_KEY,
                "rcept_no": rcept_no
            }
            
            # 과도한 트래픽 요청 방지 (0.5초 대기)
            time.sleep(0.5)
            
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
            except Exception as e:
                print(f"API 연결 오류로 건너뜁니다: {e}")
                continue

            # 2. 방어적 코드: 다운로드된 바이너리가 진짜 ZIP 파일인지 검증
            if not zipfile.is_zipfile(io.BytesIO(response.content)):
                # ZIP이 아니라면 OpenDART가 에러 메시지(XML)를 반환한 것입니다.
                try:
                    err_soup = BeautifulSoup(response.content, "lxml-xml")
                    err_msg = err_soup.find("message").text if err_soup.find("message") else "알 수 없는 API 에러"
                    print(f"OpenDART API 거부: {err_msg}")
                except:
                    print("올바른 ZIP 파일 포맷이 아니며 에러 파싱에도 실패했습니다.")
                continue

            # 3. ZIP 파일 압축 해제 및 내부 XML 텍스트 추출
            try:
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    file_list = z.namelist()
                    if not file_list:
                        print("ZIP 파일 내부가 비어있습니다.")
                        continue
                    
                    # 압축 파일 내의 첫 번째 메인 공시 서류를 읽음
                    raw_xml = z.read(file_list[0])
                    
                    # BeautifulSoup를 이용해 모든 XML/HTML 태그를 날리고 순수 텍스트만 추출
                    soup = BeautifulSoup(raw_xml, "lxml-xml")
                    clean_text = soup.get_text("\n", strip=True)
                    
                    if not clean_text.strip():
                        print("추출된 텍스트 본문이 비어있습니다.")
                        continue
                    
                    # 4. DB 적재 (요약은 차후 RAG LLM 워커가 처리할 수 있도록 우선 NULL 혹은 기본값 배치)
                    summary_placeholder = None 
                    
                    cursor.execute(insert_query, (rcept_no, clean_text, summary_placeholder))
                    conn.commit()
                    success_count += 1
                    
            except Exception as e:
                conn.rollback()
                print(f"본문 파싱 또는 DB 적재 중 에러 발생: {e}")
                continue
                
        print(f"성공: 총 {success_count}건의 공시 원문 텍스트 데이터가 disclosure_content 테이블에 최종 적재되었습니다.")
        
    except Exception as e:
        print(f"파이프라인 실행 중 치명적 오류 발생: {e}")
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    collect_disclosure_contents()