import unittest
import random

from graph.preferences import PreferenceGraph
from scripts.visualization_data import (
    _departure_weights, _weighted_sample_pairs, iteration_snapshot,
)


class IterationSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.graph = PreferenceGraph(
            {
                "u1": ["v1", "v2", "v3"],
                "u2": ["v2", "v3", "v1"],
                "u3": ["v3", "v1", "v2"],
            },
            {
                "v1": ["u1", "u2", "u3"],
                "v2": ["u2", "u3", "u1"],
                "v3": ["u3", "u1", "u2"],
            },
        )

    def test_departing_pairs_remove_both_people_and_repeat_deterministically(self):
        first = iteration_snapshot(self.graph, 2, removal_percent=50, seed=17)
        second = iteration_snapshot(self.graph, 2, removal_percent=50, seed=17)
        self.assertEqual(first["removed_history"], second["removed_history"])
        departed = first["removed_history"][0]["pairs"]
        self.assertEqual(len(departed), 2)
        self.assertEqual(len(first["population"]["male"]), 1)
        self.assertEqual(len(first["population"]["female"]), 1)
        for pair in departed:
            self.assertNotIn(pair["male"], first["population"]["male"])
            self.assertNotIn(pair["female"], first["population"]["female"])
        self.assertTrue(all(result["stable"] for result in first["results"].values()))
        self.assertEqual(len(self.graph.u), 3)
        self.assertEqual(len(self.graph.v), 3)

    def test_zero_removal_keeps_original_pool(self):
        snapshot = iteration_snapshot(self.graph, 4, removal_percent=0)
        self.assertEqual(snapshot["population"]["mutual_edges"], 9)
        self.assertTrue(all(not entry["pairs"] for entry in snapshot["removed_history"]))

    def test_distribution_axes_stay_fixed_across_rounds(self):
        first = iteration_snapshot(self.graph, 1)
        later = iteration_snapshot(self.graph, 3, removal_percent=50)
        self.assertEqual(first["distribution_axes"], {"max_rank": 3, "max_people": 6})
        self.assertEqual(later["distribution_axes"], first["distribution_axes"])

    def test_people_axis_uses_observed_count_not_population_limit(self):
        graph = PreferenceGraph(
            {"u1": ["v1", "v2"], "u2": ["v1", "v2"]},
            {"v1": ["u2", "u1"], "v2": ["u1", "u2"]},
        )
        first = iteration_snapshot(graph, 1)
        later = iteration_snapshot(graph, 3)
        self.assertEqual(first["distribution_axes"], {"max_rank": 2, "max_people": 3})
        self.assertEqual(later["distribution_axes"], first["distribution_axes"])

    def test_departure_draw_favors_low_average_disappointment(self):
        pairs = [("u1", "v1"), ("u2", "v2")]
        results = {"minimum_regret": {"metrics": {"assignments": {
            "u1": {"regret": 1}, "v1": {"regret": 1},
            "u2": {"regret": 4}, "v2": {"regret": 6},
        }}}}
        weights = _departure_weights(results, pairs)
        self.assertEqual(weights, [1, .2])
        low_score_draws = sum(
            _weighted_sample_pairs(pairs, weights, 1, random.Random(seed))[0] == pairs[0]
            for seed in range(1000)
        )
        self.assertGreater(low_score_draws, 750)
        self.assertEqual(
            _weighted_sample_pairs(pairs, weights, 2, random.Random(7)), pairs
        )


if __name__ == "__main__":
    unittest.main()
