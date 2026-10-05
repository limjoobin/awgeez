import unittest

from datasets.synthetic import generate_preferences
from matching.gale_shapley import gale_shapley
from matching.stability import is_stable


class GaleShapleyTests(unittest.TestCase):
    def test_both_orientations_are_stable_on_small_populations(self):
        for u_count, v_count, probability in (
            (3, 3, 1.0), (4, 4, 1.0), (5, 5, 1.0),
            (4, 3, 0.6), (3, 5, 0.4),
        ):
            for seed in range(8):
                graph = generate_preferences(
                    u_count, v_count, seed=seed,
                    acceptance_probability=probability,
                )
                for proposer in ("u", "v"):
                    with self.subTest(size=(u_count, v_count), seed=seed, proposer=proposer):
                        self.assertTrue(is_stable(graph, gale_shapley(graph, proposer)))

    def test_invalid_orientation(self):
        with self.assertRaises(ValueError):
            gale_shapley(generate_preferences(2, 2), "other")
