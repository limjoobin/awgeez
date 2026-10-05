import unittest

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

    def test_one_sided_preference_is_not_an_eligible_edge(self):
        graph = PreferenceGraph({"u1": ["v1"], "u2": []}, {"v1": []})
        self.assertEqual(graph.edges, ())
        self.assertFalse(graph.mutually_acceptable("u1", "v1"))
        self.assertEqual((len(graph.u), len(graph.v)), (2, 1))
