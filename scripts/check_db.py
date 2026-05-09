from stock_agent.db import get_connection


def main() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user, version();")
            database, user, version = cur.fetchone()

    print(f"database={database}")
    print(f"user={user}")
    print(f"version={version}")


if __name__ == "__main__":
    main()
