from stock_agent.db import get_connection


def main() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user, version();")
            database, user, version = cur.fetchone()
            cur.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector');")
            vector_enabled = cur.fetchone()[0]
            cur.execute("SELECT to_regclass('public.rag_documents'), to_regclass('public.rag_chunks');")
            rag_documents, rag_chunks = cur.fetchone()

    print(f"database={database}")
    print(f"user={user}")
    print(f"version={version}")
    print(f"pgvector={vector_enabled}")
    print(f"rag_documents={rag_documents is not None}")
    print(f"rag_chunks={rag_chunks is not None}")


if __name__ == "__main__":
    main()
