import unittest

from graph.preferences import PreferenceGraph
from matching.stability import Matching, blocking_pairs, is_stable


class StabilityTests(unittest.TestCase):
    def setUp(self):
        self.graph = PreferenceGraph(
            {"u1": ["v1", "v2"], "u2": ["v2", "v1"]},
            {"v1": ["u1", "u2"], "v2": ["u2", "u1"]},
        )

    def test_known_stable_and_blocking_pair(self):
        stable = Matching.from_pairs(self.graph, [("u1", "v1"), ("u2", "v2")])
        crossed = Matching.from_pairs(self.graph, [("u1", "v2"), ("u2", "v1")])
        self.assertTrue(is_stable(self.graph, stable))
        self.assertEqual(blocking_pairs(self.graph, crossed), [("u1", "v1"), ("u2", "v2")])

    def test_unmatched_participants_can_block(self):
        empty = Matching.from_pairs(self.graph, [])
        self.assertEqual(len(blocking_pairs(self.graph, empty)), 4)

    def test_invalid_matching_is_rejected(self):
        with self.assertRaises(ValueError):
            Matching.from_pairs(self.graph, [("u1", "v1"), ("u2", "v1")])
        with self.assertRaises(ValueError):
            is_stable(self.graph, Matching({"u1": "v1"}, {"v1": "u1", "v2": None}))
