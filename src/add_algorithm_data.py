"""Add real algorithm names with entirely simulated timing and usage data."""

from datetime import datetime, timedelta
from pathlib import Path
import random
import shutil
import sqlite3

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIRECTORY = PROJECT_ROOT / "data"

# Fictional workflow failures for learning, not diagnosed vendor defects.
ERROR_REASONS = [
    ("Incomplete image series", "The AI service received only part of the image series, so it could not complete processing."),
    ("Missing image metadata", "Required image metadata was missing, so the AI service could not validate the input."),
    ("Processing timeout", "The AI job exceeded the mock processing time limit before producing a usable result."),
    ("Processing service unavailable", "The AI processing service was unavailable when the study was submitted."),
    ("Unreadable image data", "The AI service could not decode the submitted image data, so processing stopped."),
]


def add_error_details(studies: pd.DataFrame) -> pd.DataFrame:
    """Add repeatable mock reasons without changing any existing study metrics."""
    enriched = studies.copy()
    enriched["ai_error_reason"] = None
    enriched["ai_error_detail"] = None
    for index, study in enriched.iterrows():
        if study["ai_error"] == 1:
            # A separate seed per study keeps reasons stable and does not alter
            # the random numbers used to generate algorithms or timings.
            reason, detail = random.Random(f"error-v1-{study['study_id']}").choice(ERROR_REASONS)
            enriched.at[index, "ai_error_reason"] = reason
            enriched.at[index, "ai_error_detail"] = detail
    return enriched


def add_algorithm_data(studies: pd.DataFrame) -> pd.DataFrame:
    """Assign at most one matching example algorithm to each mock study."""
    rng = random.Random(20260918)
    catalog = pd.read_csv(DATA_DIRECTORY / "ai_algorithms.csv")
    enriched = studies.copy()
    for index, study in enriched.iterrows():
        protocol = "Routine imaging"
        if study["modality"] == "CT" and study["body_part"] == "Head":
            protocol = "NCCT head"
        elif study["modality"] == "CT" and study["body_part"] == "Chest":
            if rng.random() < 0.7:
                protocol = "CT pulmonary angiography"
        elif study["modality"] == "MRI" and study["body_part"] == "Head":
            protocol = "Brain MRI T1 and FLAIR"

        # Match modality, body part, and mock protocol instead of assigning a
        # head-CT algorithm to an unrelated exam. These are simplified rules,
        # not complete product indications or real deployment requirements.
        choices = catalog[
            (catalog["modality"] == study["modality"])
            & (catalog["body_part"] == study["body_part"])
            & (catalog["mock_protocol"] == protocol)
        ].to_dict("records")
        algorithm = rng.choice(choices) if choices else None
        enriched.at[index, "protocol"] = protocol
        enriched.at[index, "algorithm_name"] = algorithm["algorithm_name"] if algorithm else None
        enriched.at[index, "algorithm_vendor"] = algorithm["vendor"] if algorithm else None

        eligible = algorithm is not None
        processed = eligible and rng.random() < 0.85
        error = processed and rng.random() < 0.06
        available = processed and not error
        start = datetime.fromisoformat(study["study_start_time"])
        complete = datetime.fromisoformat(study["study_complete_time"])
        ai_start = start + timedelta(seconds=rng.randint(60, 720)) if processed else None
        ai_result = ai_start + timedelta(seconds=rng.randint(30, 900)) if available else None
        # All vendors share these invented distributions. No real performance
        # statistics are used, and original study completion times stay intact.
        used = available and ai_result <= complete and rng.random() < 0.72
        for column, value in {
            "ai_eligible": eligible, "ai_processed": processed,
            "ai_error": error, "ai_result_available": available,
            "radiologist_used_ai": used,
            "ai_start_time": ai_start.isoformat(sep=" ") if ai_start else None,
            "ai_result_time": ai_result.isoformat(sep=" ") if ai_result else None,
        }.items():
            enriched.at[index, column] = value
    return add_error_details(enriched)


def backup_current_data() -> Path:
    """Save the current CSV and a consistent SQLite snapshot before changing data."""
    folder = DATA_DIRECTORY / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    folder.mkdir(parents=True)
    csv_file = DATA_DIRECTORY / "imaging_studies.csv"
    if csv_file.exists():
        shutil.copy2(csv_file, folder / csv_file.name)
    database = DATA_DIRECTORY / "ai_implementation.db"
    if database.exists():
        with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as source:
            with sqlite3.connect(folder / database.name) as destination:
                source.backup(destination)
    return folder


def main() -> None:
    """Enrich the existing 500 studies, preserving their IDs and study durations."""
    studies = pd.read_csv(DATA_DIRECTORY / "imaging_studies.csv")
    enriched = add_algorithm_data(studies)
    backup = backup_current_data()
    enriched.to_csv(DATA_DIRECTORY / "imaging_studies.csv", index=False)
    print(f"Backup saved in: {backup}")
    print(f"Added algorithm assignments to {len(enriched)} mock studies.")
    print("Run src/load_to_sqlite.py next.")


if __name__ == "__main__":
    main()
