import unittest

from matching.gale_shapley import gale_shapley
from matching.stability import is_stable
from tests.fixtures import SMALL_GRAPHS


class GaleShapleyTests(unittest.TestCase):
    def test_both_orientations_are_stable_on_small_populations(self):
        for name, graph in SMALL_GRAPHS:
            for proposer in ("u", "v"):
                with self.subTest(graph=name, proposer=proposer):
                    self.assertTrue(is_stable(graph, gale_shapley(graph, proposer)))

    def test_invalid_orientation(self):
        with self.assertRaises(ValueError):
            gale_shapley(SMALL_GRAPHS[0][1], "other")
