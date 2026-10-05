import csv
import tempfile
import unittest
from pathlib import Path

from datasets.speed_dating import (
    ATTRIBUTES, WEIGHT_COLUMNS, available_waves,
    preprocess_speed_dating_wave,
)
from matching.gale_shapley import gale_shapley
from matching.minimum_regret import minimum_regret
from matching.stability import is_stable


REAL_CSV = (
    Path(__file__).resolve().parents[1]
    / "data" / "speed-dating-experiment" / "Speed Dating Data.csv"
)


class SpeedDatingTests(unittest.TestCase):
    def test_unequal_wave_missing_pid_and_missing_like(self):
        rows = [
            ("2", "1", "1", "0", "3", "1", "1", "8"),
            ("2", "2", "2", "0", "3", "1", "0", "9"),
            ("2", "3", "1", "1", "1", "1", "1", "7"),
            ("2", "3", "1", "1", "", "2", "1", ""),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dates.csv"
            with path.open("w", encoding="cp1252", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(("wave", "iid", "id", "gender", "pid", "partner", "dec", "like", *ATTRIBUTES, *WEIGHT_COLUMNS))
                writer.writerows((*row, *("5" for _ in ATTRIBUTES), *("1" for _ in WEIGHT_COLUMNS)) for row in rows)
            self.assertEqual(available_waves(path), [2])
            graph, report, _ = preprocess_speed_dating_wave(path, 2)
        self.assertEqual((len(graph.u), len(graph.v)), (2, 1))
        self.assertEqual(graph.edges, (("u1", "v3"),))
        self.assertEqual(graph.u_preferences["u2"], ("v3",))
        self.assertEqual(graph.v_preferences["v3"], ("u1",))
        self.assertEqual(report.missing_partner_ids, 1)
        self.assertEqual(report.unresolved_partner_rows, 0)
        self.assertEqual(report.missing_like, 1)
        for matching in (gale_shapley(graph, "u"), gale_shapley(graph, "v"), minimum_regret(graph)):
            self.assertTrue(is_stable(graph, matching))

    @unittest.skipUnless(REAL_CSV.exists(), "Downloaded speed-dating CSV is absent")
    def test_downloaded_data_has_unequal_and_unresolved_waves(self):
        graph, report, _ = preprocess_speed_dating_wave(REAL_CSV, 2)
        self.assertEqual((report.rows, len(graph.u), len(graph.v), len(graph.edges)),
                         (608, 19, 16, 295))
        self.assertGreater(report.attribute_resolved_groups, 0)
        _, wave_five, _ = preprocess_speed_dating_wave(REAL_CSV, 5)
        self.assertEqual(wave_five.unresolved_partner_rows, 10)
        self.assertEqual(wave_five.yes_decisions, 95)

    def test_attribute_weights_break_like_tie_for_rated_no_dates(self):
        rows = [
            ("2", "1", "1", "0", "3", "1", "0", "8", "9", "1", "1", "1", "1", "1"),
            ("2", "1", "1", "0", "4", "2", "0", "8", "1", "9", "1", "1", "1", "1"),
            ("2", "3", "1", "1", "1", "1", "0", "7", "5", "5", "5", "5", "5", "5"),
            ("2", "4", "2", "1", "1", "1", "0", "7", "5", "5", "5", "5", "5", "5"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dates.csv"
            with path.open("w", encoding="cp1252", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(("wave", "iid", "id", "gender", "pid", "partner", "dec", "like", *ATTRIBUTES, *WEIGHT_COLUMNS))
                writer.writerows((*row, "1", "9", "0", "0", "0", "0") if row[1] == "1"
                                 else (*row, "1", "1", "1", "1", "1", "1") for row in rows)
            graph, report, scores = preprocess_speed_dating_wave(path, 2)
            missing_attribute_rows = [
                (*row[:8], "", *row[9:]) if row[1] == "1" and row[4] == "4" else row
                for row in rows
            ]
            with path.open("w", encoding="cp1252", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(("wave", "iid", "id", "gender", "pid", "partner", "dec", "like", *ATTRIBUTES, *WEIGHT_COLUMNS))
                writer.writerows((*row, "1", "9", "0", "0", "0", "0") if row[1] == "1"
                                 else (*row, "1", "1", "1", "1", "1", "1")
                                 for row in missing_attribute_rows)
            fallback_graph, fallback_report, _ = preprocess_speed_dating_wave(path, 2)
        self.assertEqual(graph.u_preferences["u1"], ("v4", "v3"))
        self.assertEqual(graph.edges, (("u1", "v4"), ("u1", "v3")))
        self.assertEqual(report.yes_decisions, 0)
        self.assertEqual(report.attribute_resolved_groups, 1)
        self.assertGreater(scores.attributes["u1"]["v4"], scores.attributes["u1"]["v3"])
        self.assertEqual(fallback_graph.u_preferences["u1"], ("v3", "v4"))
        self.assertEqual(fallback_report.attribute_fallback_groups, 1)
