"""Negative tests prove that the portfolio validator catches bad data."""

from pathlib import Path
import sys
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from validate_data import validate_rows


class DataValidationTests(unittest.TestCase):
    def setUp(self):
        self.studies = pd.read_csv(ROOT / "data/imaging_studies.csv")
        self.catalog = pd.read_csv(ROOT / "data/ai_algorithms.csv")

    def test_current_data_passes(self):
        validate_rows(self.studies, self.catalog)

    def test_duplicate_study_is_rejected(self):
        self.studies.loc[1, "study_id"] = self.studies.loc[0, "study_id"]
        with self.assertRaisesRegex(ValueError, "unique"):
            validate_rows(self.studies, self.catalog)

    def test_missing_error_explanation_is_rejected(self):
        index = self.studies.index[self.studies.ai_error == 1][0]
        self.studies.loc[index, "ai_error_detail"] = " "
        with self.assertRaisesRegex(ValueError, "explain every failure"):
            validate_rows(self.studies, self.catalog)

    def test_reversed_timestamps_are_rejected(self):
        self.studies.loc[0, "study_complete_time"] = "2000-01-01 00:00:00"
        with self.assertRaisesRegex(ValueError, "completion precedes"):
            validate_rows(self.studies, self.catalog)

    def test_ineligible_processing_is_rejected(self):
        index = self.studies.index[self.studies.ai_processed == 1][0]
        self.studies.loc[index, "ai_eligible"] = False
        with self.assertRaisesRegex(ValueError, "requires eligibility"):
            validate_rows(self.studies, self.catalog)

    def test_mismatched_algorithm_is_rejected(self):
        index = self.studies.index[self.studies.ai_eligible == 1][0]
        self.studies.loc[index, "protocol"] = "Wrong protocol"
        with self.assertRaisesRegex(ValueError, "Algorithm/protocol mismatch"):
            validate_rows(self.studies, self.catalog)


if __name__ == "__main__":
    unittest.main()
