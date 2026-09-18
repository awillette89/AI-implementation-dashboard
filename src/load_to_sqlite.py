"""Load the mock imaging-study CSV file into a local SQLite database."""

from pathlib import Path
import sqlite3

import pandas as pd


# Build paths from this script's location so the command works from the project folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = PROJECT_ROOT / "data" / "imaging_studies.csv"
DATABASE_FILE = PROJECT_ROOT / "data" / "ai_implementation.db"


def main() -> None:
    """Read the CSV and replace the database table with its current contents."""
    if not CSV_FILE.exists():
        raise FileNotFoundError(
            f"Could not find {CSV_FILE}. Run generate_mock_data.py first."
        )

    # Pandas reads the CSV into a table-like DataFrame in memory.
    studies = pd.read_csv(CSV_FILE)

    # SQLite stores the data in one portable .db file. 'replace' recreates the
    # table each time, keeping it in sync with the latest generated CSV.
    with sqlite3.connect(DATABASE_FILE) as connection:
        studies.to_sql("imaging_studies", connection, if_exists="replace", index=False)

        # This is a first, simple SQL query: COUNT(*) counts every table row.
        cursor = connection.execute("SELECT COUNT(*) FROM imaging_studies")
        database_row_count = cursor.fetchone()[0]

    print(f"Loaded {len(studies)} rows into: {DATABASE_FILE}")
    print(f"Verification query: imaging_studies contains {database_row_count} rows.")


if __name__ == "__main__":
    main()
