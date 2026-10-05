import unittest

from evaluation.metrics import evaluate
from graph.preferences import PreferenceGraph
from matching.stability import Matching


class MetricsTests(unittest.TestCase):
    def test_matched_regret_and_unmatched_count(self):
        graph = PreferenceGraph(
            {"u1": ["v1"], "u2": []}, {"v1": ["u1"]}
        )
        matching = Matching.from_pairs(graph, [("u1", "v1")])
        metrics = evaluate(graph, matching)
        self.assertEqual(metrics.regret_distribution, {1: 2})
        self.assertEqual(metrics.matched_participants, 2)
        self.assertEqual(metrics.unmatched_participants, 1)
        self.assertEqual(metrics.assignments["u2"].partner, None)
        self.assertEqual(metrics.assignments["u2"].regret, None)
        self.assertEqual(metrics.maximum_regret, 1)
        self.assertEqual(metrics.total_regret, 2)
        self.assertEqual(metrics.mean_regret, 1)
        self.assertEqual(metrics.median_regret, 1)

    def test_no_matches_has_empty_statistics(self):
        graph = PreferenceGraph({"u1": []}, {"v1": []})
        metrics = evaluate(graph, Matching.from_pairs(graph, []))
        self.assertIsNone(metrics.maximum_regret)
        self.assertIsNone(metrics.mean_regret)
        self.assertIsNone(metrics.median_regret)
        self.assertEqual(metrics.blocking_pair_count, 0)
