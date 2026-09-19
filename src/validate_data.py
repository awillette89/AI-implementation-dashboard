"""Read-only portfolio checks: python src/validate_data.py.

Checks use the underlying rows independently of the SQL formulas, so a wrong
denominator or missing filter can fail even when the dashboard still renders.
"""

from contextlib import closing
from pathlib import Path

import pandas as pd

import summarize_metrics as metrics
from run_sql_file import read_select_statements

ROOT = Path(__file__).resolve().parents[1]
FLAGS = ["ai_eligible", "ai_processed", "ai_error", "ai_result_available", "radiologist_used_ai"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_rows(studies: pd.DataFrame, catalog: pd.DataFrame) -> None:
    """Check study identity, eligibility, timing and failure explanations."""
    required = set(FLAGS + ["study_id", "site", "modality", "body_part", "protocol",
        "algorithm_name", "algorithm_vendor", "study_start_time", "study_complete_time",
        "ai_start_time", "ai_result_time", "ai_error_reason", "ai_error_detail"])
    require(required.issubset(studies.columns), "Missing required study columns.")
    require(len(studies) > 0, "Study dataset is empty.")
    require(studies.study_id.notna().all() and studies.study_id.is_unique, "Study IDs must be nonempty and unique.")
    require(catalog.algorithm_name.is_unique, "Catalog algorithm names must be unique.")
    for flag in FLAGS:
        require(studies[flag].isin([0, 1]).all(), f"{flag} must contain only true/false values.")
    eligible = studies.ai_eligible == 1
    processed = studies.ai_processed == 1
    error = studies.ai_error == 1
    available = studies.ai_result_available == 1
    used = studies.radiologist_used_ai == 1
    require((~processed | eligible).all(), "Processing requires eligibility.")
    require((~error | processed).all(), "An AI error requires a processed study.")
    require((available == (processed & ~error)).all(), "Result availability conflicts with processing/error flags.")
    require((~used | available).all(), "Adoption requires an available result.")
    require((eligible == studies.algorithm_name.notna()).all(), "Eligibility must match an algorithm assignment.")
    for column in ["ai_error_reason", "ai_error_detail"]:
        present = studies[column].fillna("").str.strip().ne("")
        require((present == error).all(), f"{column} must explain every failure and no successful study.")

    start = pd.to_datetime(studies.study_start_time, errors="coerce")
    complete = pd.to_datetime(studies.study_complete_time, errors="coerce")
    ai_start = pd.to_datetime(studies.ai_start_time, errors="coerce")
    result = pd.to_datetime(studies.ai_result_time, errors="coerce")
    require(start.notna().all() and complete.notna().all(), "Invalid study timestamps.")
    require((complete >= start).all(), "Study completion precedes study start.")
    require((ai_start.notna() == processed).all(), "AI start timestamps must match attempted processing.")
    require((result.notna() == available).all(), "AI result timestamps must match successful results.")
    require((ai_start[processed] >= start[processed]).all(), "AI starts before its study.")
    require((result[available] >= ai_start[available]).all(), "AI result precedes AI start.")
    require((result[used] <= complete[used]).all(), "A result used during reading arrives after study completion.")
    products = catalog.set_index("algorithm_name")
    for row in studies[eligible].itertuples():
        require(row.algorithm_name in products.index, "Assigned algorithm is absent from catalog.")
        product = products.loc[row.algorithm_name]
        require((row.algorithm_vendor, row.modality, row.body_part, row.protocol) ==
                (product.vendor, product.modality, product.body_part, product.mock_protocol),
                f"Algorithm/protocol mismatch for {row.study_id}.")


def close_enough(actual, expected, label: str) -> None:
    # SQL uses floating-point Julian dates and one-decimal rounding. Compare to
    # the unrounded independent mean within half of the displayed decimal unit.
    if expected is None:
        require(actual is None, f"{label}: an undefined value must be NULL.")
    else:
        require(actual is not None and abs(actual - expected) <= 0.05001,
                f"{label}: expected approximately {expected}, got {actual}.")


def percentage(numerator: int, denominator: int):
    return 100 * numerator / denominator if denominator else None


def validate_reports(studies: pd.DataFrame) -> None:
    """Reconcile all site scopes, charts, error lists and algorithm timings."""
    for site in [None, *metrics.load_sites()]:
        rows = studies if site is None else studies[studies.site == site]
        actual = metrics.load_overall_metrics(site)
        eligible = rows[rows.ai_eligible == 1]
        processed = rows[rows.ai_processed == 1]
        available = rows[rows.ai_result_available == 1]
        error_count = int(processed.ai_error.sum())
        eligible_processed = int(eligible.ai_processed.sum())
        adopted = int(available.radiologist_used_ai.sum())
        require(actual["Studies processed"]["total_studies_processed"] == len(rows), "Study count mismatch.")
        count_fields = [
            ("AI utilization", "ai_eligible_studies", len(eligible)),
            ("AI utilization", "eligible_studies_ai_processed", eligible_processed),
            ("AI error rate", "ai_processed_studies", len(processed)),
            ("AI error rate", "ai_error_studies", error_count),
            ("AI adoption", "ai_result_available_studies", len(available)),
            ("AI adoption", "radiologist_used_ai_studies", adopted),
        ]
        for report, column, expected in count_fields:
            require((actual[report][column] or 0) == expected, f"{site}: {column} mismatch.")
        for report, column, numerator, denominator in [
            ("AI utilization", "ai_utilization_percent", eligible_processed, len(eligible)),
            ("AI error rate", "ai_error_rate_percent", error_count, len(processed)),
            ("AI adoption", "ai_adoption_rate_percent", adopted, len(available)),
        ]:
            close_enough(actual[report][column], percentage(numerator, denominator), column)
        minutes = (pd.to_datetime(rows.study_complete_time) - pd.to_datetime(rows.study_start_time)).dt.total_seconds() / 60
        close_enough(actual["Turnaround time"]["avg_turnaround_minutes"], minutes.mean(), "Study TAT")
        volumes = {r["modality"]: r["study_count"] for r in metrics.load_modality_volumes(site)}
        require(volumes == rows.groupby("modality").size().to_dict(), "Volume chart mismatch.")
        usage = metrics.load_modality_utilization(site)
        require({r["modality"] for r in usage} == set(eligible.modality), "Utilization modality mismatch.")
        for result in usage:
            group = eligible[eligible.modality == result["modality"]]
            require(result["ai_eligible_studies"] == len(group), "Utilization denominator mismatch.")
            require(result["eligible_studies_ai_processed"] == int(group.ai_processed.sum()), "Utilization numerator mismatch.")
            close_enough(result["ai_utilization_percent"], percentage(group.ai_processed.sum(), len(group)), "Modality utilization")
        failures = metrics.load_error_details(site)
        require({r["study_id"] for r in failures} == set(processed[processed.ai_error == 1].study_id), "Error list mismatch.")
        timings = metrics.load_algorithm_turnaround(site)
        require(sum(r["ai_processed_studies"] for r in timings) == len(processed), "Algorithm counts mismatch.")
        for result in timings:
            group = processed[processed.algorithm_name == result["algorithm_name"]]
            success = group[group.ai_result_available == 1]
            require(result["successful_results"] == len(success), "Successful-result count mismatch.")
            require(result["ai_errors"] == int(group.ai_error.sum()), "Algorithm error count mismatch.")
            ai_minutes = (pd.to_datetime(success.ai_result_time) - pd.to_datetime(success.ai_start_time)).dt.total_seconds() / 60
            tat = (pd.to_datetime(group.study_complete_time) - pd.to_datetime(group.study_start_time)).dt.total_seconds() / 60
            close_enough(result["avg_ai_processing_minutes"], ai_minutes.mean() if len(success) else None, "Algorithm processing TAT")
            close_enough(result["avg_study_turnaround_minutes"], tat.mean(), "Algorithm study TAT")


def main() -> None:
    studies = pd.read_csv(ROOT / "data/imaging_studies.csv")
    catalog = pd.read_csv(ROOT / "data/ai_algorithms.csv")
    validate_rows(studies, catalog)
    print("PASS: study IDs, algorithm matching, AI flags, timestamps and error explanations")
    with closing(metrics.open_database()) as connection:
        require(connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite integrity check failed.")
        stored = pd.read_sql_query("SELECT * FROM imaging_studies ORDER BY study_id", connection)
        pd.testing.assert_frame_equal(studies.sort_values("study_id").reset_index(drop=True), stored, check_dtype=False)
        for report in sorted((ROOT / "sql").glob("*.sql")):
            for query in read_select_statements(report):
                connection.execute(query).fetchall()
    print("PASS: CSV/database agreement, SQLite integrity and all standalone SQL reports")
    validate_reports(studies)
    print("PASS: independent metric calculations, all sites, chart counts and algorithm TAT")
    require(metrics.load_error_details("__no_such_site__") == [], "Empty-site error list failed.")
    require(metrics.load_algorithm_turnaround("__no_such_site__") == [], "Empty-site algorithm list failed.")
    empty = metrics.load_overall_metrics("__no_such_site__")
    for report, column in [("AI utilization", "ai_utilization_percent"), ("AI error rate", "ai_error_rate_percent"),
                           ("AI adoption", "ai_adoption_rate_percent"), ("Turnaround time", "avg_turnaround_minutes")]:
        require(empty[report][column] is None, "No-data metrics must remain undefined.")
    print(f"PASS: empty selections; validated {len(studies)} simulated studies without modifying data")


if __name__ == "__main__":
    main()
