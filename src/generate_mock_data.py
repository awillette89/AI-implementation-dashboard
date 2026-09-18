"""Generate a small, realistic mock dataset for the AI implementation project."""

from datetime import datetime, timedelta
from pathlib import Path
import random

import pandas as pd


# A fixed seed makes the same example data every time the script is run.
random.seed(42)

NUMBER_OF_STUDIES = 500
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = PROJECT_ROOT / "data" / "imaging_studies.csv"


def random_datetime(start: datetime, end: datetime) -> datetime:
    """Return one random time between start and end."""
    seconds_between = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, seconds_between))


def generate_study(study_number: int) -> dict:
    """Create one imaging study while keeping the workflow fields consistent."""
    study_start = random_datetime(datetime(2026, 1, 1), datetime(2026, 3, 31, 23, 59))
    modality = random.choices(["CT", "MRI", "X-ray", "Ultrasound"], weights=[45, 25, 20, 10])[0]
    body_part = random.choice(["Chest", "Head", "Abdomen", "Spine", "Extremity"])

    # Only selected study types are eligible for the fictional AI tool.
    ai_eligible = modality in {"CT", "MRI"} and body_part in {"Chest", "Head", "Abdomen"}
    ai_processed = ai_eligible and random.random() < 0.82

    ai_start = None
    ai_result = None
    ai_error = False
    ai_result_available = False

    if ai_processed:
        ai_start = study_start + timedelta(minutes=random.randint(1, 12))
        ai_error = random.random() < 0.04
        if not ai_error:
            ai_result = ai_start + timedelta(minutes=random.randint(2, 15))
            ai_result_available = True

    # Completion happens after the study starts, regardless of AI participation.
    completion_minutes = random.randint(35, 240)
    study_complete = study_start + timedelta(minutes=completion_minutes)

    # A radiologist can use AI only when a usable AI result is available.
    radiologist_used_ai = ai_result_available and random.random() < 0.72

    return {
        "study_id": f"ST{study_number:05d}",
        "study_date": study_start.date().isoformat(),
        "modality": modality,
        "body_part": body_part,
        "site": random.choice(["Central Hospital", "North Clinic", "South Imaging Center"]),
        "ai_eligible": ai_eligible,
        "ai_processed": ai_processed,
        "ai_result_available": ai_result_available,
        "ai_error": ai_error,
        "study_start_time": study_start.isoformat(sep=" "),
        "ai_start_time": ai_start.isoformat(sep=" ") if ai_start else None,
        "ai_result_time": ai_result.isoformat(sep=" ") if ai_result else None,
        "study_complete_time": study_complete.isoformat(sep=" "),
        "radiologist_used_ai": radiologist_used_ai,
    }


def main() -> None:
    """Create 500 studies and write them to the project's data folder."""
    studies = [generate_study(number) for number in range(1, NUMBER_OF_STUDIES + 1)]
    dataset = pd.DataFrame(studies)

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    dataset.to_csv(OUTPUT_FILE, index=False)
    print(f"Created {len(dataset)} mock studies at: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
