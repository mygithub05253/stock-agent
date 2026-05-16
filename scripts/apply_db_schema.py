from pathlib import Path

from stock_agent.db import get_connection


def main() -> None:
    schema_dir = Path(__file__).resolve().parents[1] / "db" / "init"
    sql_files = sorted(schema_dir.glob("*.sql"))

    with get_connection() as conn:
        with conn.cursor() as cur:
            for sql_file in sql_files:
                cur.execute(sql_file.read_text(encoding="utf-8"))
                print(f"applied={sql_file.name}")

    print("schema=ok")


if __name__ == "__main__":
    main()
