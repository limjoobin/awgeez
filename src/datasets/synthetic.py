"""Reproducible synthetic preference lists."""

from random import Random

from graph.preferences import PreferenceGraph


def generate_preferences(
    u_count: int,
    v_count: int,
    *,
    seed: int = 0,
    acceptance_probability: float = 1.0,
) -> PreferenceGraph:
    if u_count < 0 or v_count < 0:
        raise ValueError("Population sizes must be nonnegative")
    if not 0 <= acceptance_probability <= 1:
        raise ValueError("acceptance_probability must be between 0 and 1")
    rng = Random(seed)
    u = [f"u{i}" for i in range(1, u_count + 1)]
    v = [f"v{i}" for i in range(1, v_count + 1)]

    def make_lists(people: list[str], candidates: list[str]) -> dict[str, list[str]]:
        result = {}
        for person in people:
            shuffled = candidates.copy()
            rng.shuffle(shuffled)
            result[person] = [
                candidate for candidate in shuffled
                if rng.random() < acceptance_probability
            ]
        return result

    return PreferenceGraph(make_lists(u, v), make_lists(v, u))
