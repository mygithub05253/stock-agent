import os
import time
import psycopg2
from dotenv import load_dotenv

# 뉴스 임베딩 생성 파이프라인
# rag_documents에 저장된 뉴스 content를 읽어서
# pgvector embedding 생성을 위한 전처리를 수행합니다.
#
# 현재 MVP 단계에서는:
# - chunk 생성
# - 임베딩 대상 준비
# - rag_chunks 저장
#
# 까지 우선 구현합니다.
#
# 실제 OpenAI/OpenRouter embedding 호출은
# 추후 API 키 확정 후 연결 예정입니다.

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def split_text(text, chunk_size=500, overlap=100):
    """
    긴 텍스트를 chunk 단위로 분할합니다.

    MVP 단계에서는 단순 문자 기준 분할 사용.
    이후 LangChain RecursiveCharacterTextSplitter 등으로 교체 가능.
    """
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk.strip())

        start += chunk_size - overlap

    return chunks


def fetch_rag_documents(cursor, limit=1000):
    """
    chunk 생성 대상 문서를 가져옵니다.
    """
    cursor.execute("""
        SELECT
            document_id,
            source_type,
            source,
            external_id,
            corp_code,
            stock_code,
            title,
            content,
            published_at
        FROM rag_documents
        WHERE content IS NOT NULL
        ORDER BY published_at DESC
        LIMIT %s;
    """, (limit,))

    return cursor.fetchall()


def insert_chunk(
    cursor,
    document_id,
    chunk_index,
    chunk_text,
    published_at,
    stock_code,
    corp_code,
):
    """
    rag_chunks 테이블에 chunk 저장.

    현재는 embedding 없이 저장만 수행.
    추후 pgvector embedding 컬럼 연결 예정.
    """

    query = """
        INSERT INTO rag_chunks (
            document_id,
            chunk_index,
            content,
            published_at,
            stock_code,
            corp_code
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (document_id, chunk_index)
        DO UPDATE SET
            content = EXCLUDED.content,
            published_at = EXCLUDED.published_at,
            stock_code = EXCLUDED.stock_code,
            corp_code = EXCLUDED.corp_code,
            updated_at = NOW();
    """

    cursor.execute(
        query,
        (
            document_id,
            chunk_index,
            chunk_text,
            published_at,
            stock_code,
            corp_code,
        )
    )


def embed_news():
    """
    뉴스 임베딩 전처리 전체 실행 함수.
    rag_documents → rag_chunks 흐름을 담당합니다.
    """
    print("뉴스 임베딩 전처리 파이프라인 시작...")

    if not DATABASE_URL:
        print("DATABASE_URL 누락")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return

    try:
        documents = fetch_rag_documents(cursor, limit=1000)

        if not documents:
            print("임베딩 대상 문서가 없습니다.")
            return

        print(f"임베딩 대상 문서 수: {len(documents)}건")

        total_chunks = 0

        for idx, row in enumerate(documents, 1):
            (
                document_id,
                source_type,
                source,
                external_id,
                corp_code,
                stock_code,
                title,
                content,
                published_at,
            ) = row

            try:
                chunks = split_text(
                    text=content,
                    chunk_size=500,
                    overlap=100,
                )

                for chunk_index, chunk_text in enumerate(chunks):
                    insert_chunk(
                        cursor=cursor,
                        document_id=document_id,
                        chunk_index=chunk_index,
                        chunk_text=chunk_text,
                        published_at=published_at,
                        stock_code=stock_code,
                        corp_code=corp_code,
                    )

                total_chunks += len(chunks)

                if idx % 50 == 0:
                    conn.commit()
                    print(f"  -> {idx}/{len(documents)} 문서 처리 중...")

            except Exception as e:
                print(f"  -> 문서 chunk 생성 실패 document_id={document_id}: {e}")

            time.sleep(0.05)

        conn.commit()

        print(f"최종 완료: 총 {total_chunks}개 chunk 생성 완료")

    except Exception as e:
        conn.rollback()
        print(f"치명적 오류 발생: {e}")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    embed_news()
