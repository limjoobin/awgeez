import unittest

from evaluation.metrics import evaluate
from graph.preferences import PreferenceGraph
from matching.gale_shapley import gale_shapley
from matching.minimum_regret import minimum_regret
from matching.stability import is_stable
from tests.oracle import exhaustive_best
from tests.fixtures import SMALL_GRAPHS


class MinimumRegretTests(unittest.TestCase):
    def test_cp_sat_matches_exhaustive_oracle(self):
        for name, graph in SMALL_GRAPHS:
            with self.subTest(graph=name):
                matching = minimum_regret(graph)
                metrics = evaluate(graph, matching)
                oracle_score, _ = exhaustive_best(graph)
                self.assertTrue(is_stable(graph, matching))
                self.assertEqual(
                    (metrics.maximum_regret, metrics.total_regret), oracle_score
                )

    def test_minimax_can_improve_on_gale_shapley(self):
        graph = PreferenceGraph(
            {
                "u1": ["v2", "v3", "v1"],
                "u2": ["v3", "v1", "v2"],
                "u3": ["v1", "v3", "v2"],
            },
            {
                "v1": ["u1", "u2", "u3"],
                "v2": ["u2", "u1", "u3"],
                "v3": ["u3", "u1", "u2"],
            },
        )
        self.assertEqual(evaluate(graph, gale_shapley(graph, "u")).maximum_regret, 3)
        self.assertEqual(evaluate(graph, minimum_regret(graph)).maximum_regret, 2)

    def test_secondary_total_regret_breaks_minimax_tie(self):
        graph = PreferenceGraph(
            {
                "u1": ["v1", "v3", "v2"],
                "u2": ["v2", "v3", "v1"],
                "u3": ["v2", "v3", "v1"],
            },
            {
                "v1": ["u3", "u2", "u1"],
                "v2": ["u3", "u1", "u2"],
                "v3": ["u1", "u3", "u2"],
            },
        )
        gs = evaluate(graph, gale_shapley(graph, "u"))
        optimum = evaluate(graph, minimum_regret(graph))
        self.assertEqual((gs.maximum_regret, gs.total_regret), (3, 11))
        self.assertEqual((optimum.maximum_regret, optimum.total_regret), (3, 10))

    def test_unmatched_participants_and_empty_graph(self):
        graph = PreferenceGraph({"u1": ["v1"], "u2": []}, {"v1": ["u1"]})
        matching = minimum_regret(graph)
        score, _ = exhaustive_best(graph)
        metrics = evaluate(graph, matching)
        self.assertEqual((metrics.maximum_regret, metrics.total_regret), score)
        self.assertEqual(metrics.unmatched_participants, 1)
        self.assertIsNone(metrics.assignments["u2"].regret)
        empty = PreferenceGraph({"u1": []}, {"v1": []})
        self.assertEqual(minimum_regret(empty).pairs(), ())
