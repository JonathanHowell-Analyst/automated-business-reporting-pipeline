import sys
import unittest
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Src"))
from main import load_and_validate, validate_week, find_previous_week, BASE_DIR


class PipelineTests(unittest.TestCase):
    def test_current_week(self):
        data = load_and_validate(BASE_DIR / "Archive/sales_week_40.csv", "current")
        start = pd.Timestamp("2026-09-28")
        self.assertEqual(validate_week(data, start, "current"), pd.Timestamp("2026-10-04"))
        self.assertAlmostEqual(data["revenue"].sum(), 6335)

    def test_previous_week_selection(self):
        path, data = find_previous_week(pd.Timestamp("2026-09-28"))
        self.assertEqual(path.name, "sales_week_39.csv")
        self.assertAlmostEqual(data["revenue"].sum(), 6190)

    def test_current_reporting_week(self):
        data = load_and_validate(BASE_DIR / "Data/sales_week_48.csv", "current")
        self.assertEqual(validate_week(data, pd.Timestamp("2026-11-23"), "current"), pd.Timestamp("2026-11-29"))
        self.assertGreater(len(data), 100)

    def test_new_previous_week_selection(self):
        path, data = find_previous_week(pd.Timestamp("2026-11-23"))
        self.assertEqual(path.name, "sales_week_47.csv")
        self.assertGreater(len(data), 100)

    def test_outside_week_rejected(self):
        data = load_and_validate(BASE_DIR / "Archive/sales_week_40.csv", "current")
        data.loc[data.index[0], "date"] = pd.Timestamp("2026-09-27")
        with self.assertRaises(ValueError):
            validate_week(data, pd.Timestamp("2026-09-28"), "current")


if __name__ == "__main__":
    unittest.main()
