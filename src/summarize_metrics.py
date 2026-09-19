"""Print the five overall metrics using the existing SQL reports."""

from contextlib import closing
from pathlib import Path
import sqlite3

from run_sql_file import read_select_statements


# __file__ is this script's path, so these paths work from any terminal folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_FILE = PROJECT_ROOT / "data" / "ai_implementation.db"
SQL_DIRECTORY = PROJECT_ROOT / "sql"

# Each entry pairs a report with the columns to display from its first query.
# The calculations remain in SQL. Python only labels and formats the results.
REPORTS = [
    ("Studies processed", "01_studies_processed.sql", [
        ("Total studies", "total_studies_processed", "count"),
    ]),
    ("AI utilization", "02_ai_utilization.sql", [
        ("Eligible studies", "ai_eligible_studies", "count"),
        ("Eligible studies processed by AI", "eligible_studies_ai_processed", "count"),
        ("Utilization rate", "ai_utilization_percent", "percent"),
    ]),
    ("AI error rate", "03_ai_error_rate.sql", [
        ("AI-processed studies", "ai_processed_studies", "count"),
        ("Studies with an AI error", "ai_error_studies", "count"),
        ("Error rate", "ai_error_rate_percent", "percent"),
    ]),
    ("Turnaround time", "04_turnaround_time.sql", [
        ("Average study start to completion", "avg_turnaround_minutes", "minutes"),
    ]),
    ("AI adoption", "05_ai_adoption.sql", [
        ("Studies with an AI result available", "ai_result_available_studies", "count"),
        ("Results used by radiologists", "radiologist_used_ai_studies", "count"),
        ("Adoption rate", "ai_adoption_rate_percent", "percent"),
    ]),
]


def format_value(value: int | float | None, kind: str) -> str:
    """Show counts, percentages, and minutes in a readable form."""
    if kind == "count":
        # SUM can return NULL for an empty group. Its study count is zero.
        return f"{0 if value is None else int(value):,}"
    # SQLite's NULL becomes Python's None. Undefined rates are not zero rates.
    if value is None:
        return "N/A"
    if kind == "percent":
        return f"{value:.1f}%"
    return f"{value:.1f} minutes"


def open_database() -> sqlite3.Connection:
    """Open the existing database read-only for either display."""
    if not DATABASE_FILE.is_file():
        raise FileNotFoundError(
            f"Could not find {DATABASE_FILE}. Run src/load_to_sqlite.py first."
        )

    # connect opens SQLite. mode=ro makes this connection read-only, preventing
    # changes to the database. closing ensures it is closed when we finish.
    database_uri = DATABASE_FILE.as_uri() + "?mode=ro"
    return sqlite3.connect(database_uri, uri=True)


def load_sites() -> list[str]:
    """Read the dropdown choices from the database, in alphabetical order."""
    with closing(open_database()) as connection:
        rows = connection.execute(
            "SELECT DISTINCT site FROM imaging_studies "
            "WHERE site IS NOT NULL ORDER BY site"
        ).fetchall()
    return [row[0] for row in rows]


def load_modality_volumes(site: str | None = None) -> list[dict]:
    """Count all studies by modality, optionally limited to a single site."""
    # GROUP BY puts rows with the same modality together. COUNT(*) counts
    # every study in each group, regardless of AI eligibility or processing.
    query = "SELECT modality, COUNT(*) AS study_count FROM imaging_studies"
    parameters = ()
    if site is not None:
        # Pass the selected site separately as data, using the ? placeholder.
        query += " WHERE site = ?"
        parameters = (site,)
    query += " GROUP BY modality ORDER BY modality"
    with closing(open_database()) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, parameters).fetchall()
    return [dict(row) for row in rows]


def filter_report_by_site(query: str, site: str | None) -> tuple[str, tuple]:
    """Supply site-filtered rows to an existing report without changing its formula."""
    if site is None:
        return query, ()
    # WITH names a result just for this query. The report reads this filtered
    # imaging_studies result, while main.imaging_studies is the original table.
    # Its own WHERE still controls eligibility and other metric denominators.
    query = (
        "WITH imaging_studies AS ("
        "SELECT * FROM main.imaging_studies WHERE site = ?"
        ")\n" + query
    )
    # Pass the site separately so even names with apostrophes stay data.
    return query, (site,)


def load_modality_utilization(site: str | None = None) -> list[dict]:
    """Reuse the utilization report's modality query for the chart and table."""
    statements = read_select_statements(SQL_DIRECTORY / "02_ai_utilization.sql")
    if len(statements) < 3:
        raise ValueError("The utilization report must include its modality query.")
    # [2] is the third query: WHERE keeps eligible studies, and GROUP BY modality
    # calculates utilization separately for each imaging type. A modality with
    # no eligible studies has no remaining rows, so it is excluded automatically.
    query, parameters = filter_report_by_site(statements[2], site)
    with closing(open_database()) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, parameters).fetchall()
    return [dict(row) for row in rows]


def load_algorithm_turnaround(site: str | None = None) -> list[dict]:
    """Use the algorithm SQL report for the dashboard's TAT lookup table."""
    statements = read_select_statements(SQL_DIRECTORY / "06_algorithm_turnaround.sql")
    if not statements:
        raise ValueError("No query found in the algorithm turnaround report.")
    query, parameters = filter_report_by_site(statements[0], site)
    with closing(open_database()) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(query, parameters)]


def load_error_details(site: str | None = None) -> list[dict]:
    """Read failed studies and their mock reasons for the selected site."""
    query = """
        SELECT study_id, study_date, site, modality, algorithm_name,
               COALESCE(ai_error_reason, 'Reason not recorded') AS ai_error_reason,
               COALESCE(ai_error_detail, 'No explanation recorded.') AS ai_error_detail
        FROM imaging_studies
        WHERE ai_processed = 1 AND ai_error = 1
    """
    parameters = ()
    if site is not None:
        query += " AND site = ?"
        parameters = (site,)
    query += " ORDER BY study_date DESC, study_id"
    with closing(open_database()) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(query, parameters)]


def load_overall_metrics(site: str | None = None) -> dict[str, dict[str, int | float | None]]:
    """Return all-study or single-site results using the same SQL formulas."""
    metrics = {}
    with closing(open_database()) as connection:
        # Row lets us access values by their SQL column names instead of numbers.
        connection.row_factory = sqlite3.Row

        for title, filename, columns in REPORTS:
            statements = read_select_statements(SQL_DIRECTORY / filename)
            if not statements:
                raise ValueError(f"No SQL statements found in {filename}")

            # [0] selects the first query, which reports the overall metric.
            # execute runs that query. fetchone reads its single summary row.
            query, parameters = filter_report_by_site(statements[0], site)
            row = connection.execute(query, parameters).fetchone()
            if row is None:
                raise ValueError(f"No overall result returned by {filename}")

            # A dictionary retains the SQL column names after the connection closes.
            metrics[title] = dict(row)
    return metrics


def main() -> None:
    """Print the shared results in the original terminal summary format."""
    metrics = load_overall_metrics()
    print("AI Implementation Summary (mock data)")
    for title, filename, columns in REPORTS:
        print(f"\n{title}")
        for label, column, kind in columns:
            print(f"  {label}: {format_value(metrics[title][column], kind)}")


if __name__ == "__main__":
    main()
