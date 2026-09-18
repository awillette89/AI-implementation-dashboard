"""Run a simple SQL report file against the project's SQLite database."""

import argparse
from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_FILE = PROJECT_ROOT / "data" / "ai_implementation.db"


def read_select_statements(sql_file: Path) -> list[str]:
    """Return the semicolon-separated SQL queries from a report file.

    This intentionally small runner is for this project's simple SELECT-only
    report files. More complex SQL parsing can be added later if needed.
    """
    sql_text = sql_file.read_text(encoding="utf-8")
    statements = []

    for section in sql_text.split(";"):
        # Remove comment lines before checking whether this section has SQL.
        query_lines = [
            line for line in section.splitlines() if not line.strip().startswith("--")
        ]
        query = "\n".join(query_lines).strip()
        if query:
            statements.append(query)

    return statements


def main() -> None:
    """Run every SELECT statement in a supplied SQL file and print its table."""
    parser = argparse.ArgumentParser(description="Run a SQL report against SQLite.")
    parser.add_argument("sql_file", type=Path, help="Path to the .sql report file")
    arguments = parser.parse_args()

    sql_file = arguments.sql_file.resolve()
    if not sql_file.exists():
        raise FileNotFoundError(f"Could not find SQL file: {sql_file}")
    if not DATABASE_FILE.exists():
        raise FileNotFoundError(
            f"Could not find {DATABASE_FILE}. Run load_to_sqlite.py first."
        )

    statements = read_select_statements(sql_file)
    if not statements:
        raise ValueError(f"No SQL statements found in {sql_file}")

    with sqlite3.connect(DATABASE_FILE) as connection:
        for number, statement in enumerate(statements, start=1):
            result = pd.read_sql_query(statement, connection)
            print(f"\nResult set {number}")
            print(result.to_string(index=False))


if __name__ == "__main__":
    main()
