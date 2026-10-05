"""Read Redis and build reproducible matching snapshots for the UI."""

import math
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from graph.preferences import PreferenceGraph
from storage import RedisStore
from scripts.run_experiment import compare_graph


def available_waves() -> list[int]:
    """Discover ingested wave namespaces without reading the source CSV."""
    client = RedisStore("speed-dating-wave-1").client
    waves = set()
    for key in client.scan_iter(match="mm:speed-dating-wave-*:meta"):
        match = re.fullmatch(r"mm:speed-dating-wave-(\d+):meta", key)
        if match:
            waves.add(int(match.group(1)))
    return sorted(waves)


def _remove_pairs(graph: PreferenceGraph, pairs: list[tuple[str, str]]) -> PreferenceGraph:
    departed_u = {u for u, _ in pairs}
    departed_v = {v for _, v in pairs}
    return PreferenceGraph(
        {
            u: [v for v in graph.u_preferences[u] if v not in departed_v]
            for u in graph.u if u not in departed_u
        },
        {
            v: [u for u in graph.v_preferences[v] if u not in departed_u]
            for v in graph.v if v not in departed_v
        },
    )


def _weighted_sample_pairs(
    pairs: list[tuple[str, str]], weights: list[float], count: int,
    rng: random.Random,
) -> list[tuple[str, str]]:
    """Draw matched pairs without replacement using positive selection weights."""
    if len(pairs) != len(weights) or any(weight <= 0 for weight in weights):
        raise ValueError("each pair needs a positive selection weight")
    remaining_pairs = list(pairs)
    remaining_weights = list(weights)
    selected = []
    for _ in range(min(count, len(remaining_pairs))):
        index = rng.choices(range(len(remaining_pairs)), weights=remaining_weights)[0]
        selected.append(remaining_pairs.pop(index))
        remaining_weights.pop(index)
    return sorted(selected)


def _departure_weights(results: dict, pairs: list[tuple[str, str]]) -> list[float]:
    """Give lower average partner ranks higher departure odds."""
    assignments = results["minimum_regret"]["metrics"]["assignments"]
    return [
        2 / (assignments[u]["regret"] + assignments[v]["regret"])
        for u, v in pairs
    ]


def iteration_snapshot(
    graph: PreferenceGraph, iteration: int, removal_percent: int = 5, seed: int = 7
) -> dict:
    """Recompute every method per round; departures use minimum-regret pairs."""
    if not 1 <= iteration <= 20:
        raise ValueError("iteration must be between 1 and 20")
    if not 0 <= removal_percent <= 100:
        raise ValueError("removal_percent must be between 0 and 100")
    # Use the initial wave to keep the rank axis unchanged across rounds.
    max_rank = max(
        (len(choices) for choices in (*graph.u_preferences.values(), *graph.v_preferences.values())),
        default=1,
    )
    current = graph
    history = []
    max_count = 0
    selected_graph = graph
    selected_results = None
    # Check all UI rounds so the observed count scale stays fixed while sliding.
    last_round = max(10, iteration)
    for round_number in range(1, last_round + 1):
        results = compare_graph(current)
        for result in results.values():
            max_count = max(
                max_count,
                max(result["metrics"]["regret_distribution"].values(), default=0),
            )
        if round_number == iteration:
            selected_graph = current
            selected_results = results
        if round_number == last_round:
            break
        matched_pairs = [
            (u, v) for u, v in results["minimum_regret"]["matching"].items()
            if v is not None
        ]
        count = math.ceil(len(matched_pairs) * removal_percent / 100)
        rng = random.Random(f"{seed}:{round_number}")
        departed = _weighted_sample_pairs(
            matched_pairs, _departure_weights(results, matched_pairs), count, rng
        )
        if round_number < iteration:
            history.append({
                "after_iteration": round_number,
                "pairs": [{"female": u, "male": v} for u, v in departed],
            })
        current = _remove_pairs(current, departed)

    return {
        "iteration": iteration,
        "removal_percent": removal_percent,
        "seed": seed,
        "distribution_axes": {
            "max_rank": max(1, max_rank),
            "max_people": max(1, max_count),
        },
        "removed_history": history,
        "population": {
            "male": list(selected_graph.v),
            "female": list(selected_graph.u),
            "mutual_edges": len(selected_graph.edges),
            "edges": [
                {
                    "male": v, "female": u,
                    "male_rank": selected_graph.v_ranks[v][u],
                    "female_rank": selected_graph.u_ranks[u][v],
                }
                for u, v in selected_graph.edges
            ],
        },
        "results": selected_results,
    }


def load_iteration(wave: int, iteration: int, removal_percent: int = 5,
                   seed: int = 7) -> dict:
    """Load a wave from Redis, then compute its requested round on demand."""
    if not 1 <= wave <= 999:
        raise ValueError("wave must be a positive integer")
    store = RedisStore(f"speed-dating-wave-{wave}")
    graph = store.load_graph()
    snapshot = iteration_snapshot(graph, iteration, removal_percent, seed)
    snapshot["wave"] = wave
    snapshot["metadata"] = store.metadata()
    return snapshot
