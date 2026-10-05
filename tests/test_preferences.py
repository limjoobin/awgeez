import unittest

from datasets.synthetic import generate_preferences
from graph.preferences import PreferenceGraph


class PreferenceTests(unittest.TestCase):
    def test_ranks_keep_original_positions_for_mutual_edges(self):
        graph = PreferenceGraph(
            {"u1": ["v1", "v2"], "u2": ["v2"]},
            {"v1": [], "v2": ["u1", "u2"]},
        )
        self.assertEqual(graph.edges, (("u1", "v2"), ("u2", "v2")))
        self.assertEqual(graph.ranks("u1", "v2"), (2, 1))

    def test_invalid_input_is_rejected(self):
        with self.assertRaises(ValueError):
            PreferenceGraph({"u1": ["v1", "v1"]}, {"v1": ["u1"]})
        with self.assertRaises(ValueError):
            PreferenceGraph({"u1": ["missing"]}, {"v1": ["u1"]})
        with self.assertRaises(ValueError):
            PreferenceGraph({"same": []}, {"same": []})

    def test_generator_is_reproducible_and_supports_incomplete_lists(self):
        first = generate_preferences(4, 3, seed=7, acceptance_probability=0.5)
        second = generate_preferences(4, 3, seed=7, acceptance_probability=0.5)
        self.assertEqual(first.edges, second.edges)
        self.assertEqual(dict(first.u_preferences), dict(second.u_preferences))
        self.assertEqual(len(first.u), 4)
        self.assertEqual(len(first.v), 3)
