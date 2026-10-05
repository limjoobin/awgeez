"""Compare both Gale-Shapley orientations and exact regret optimization."""

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluation.metrics import evaluate
from graph.preferences import PreferenceGraph
from matching.gale_shapley import gale_shapley
from matching.minimum_regret import minimum_regret
from matching.stability import is_stable
from storage import RedisStore


def compare_graph(graph: PreferenceGraph) -> dict[str, dict]:
    """Run every matching approach against the same in-memory preference graph."""
    results = {}
    for name, matching in (
        ("gale_shapley_u_proposes", gale_shapley(graph, "u")),
        ("gale_shapley_v_proposes", gale_shapley(graph, "v")),
        ("minimum_regret", minimum_regret(graph)),
    ):
        stable = is_stable(graph, matching)
        if not stable:
            raise RuntimeError(f"{name} produced an unstable matching")
        result = {
            "matching": dict(matching.u_to_v),
            "stable": stable,
            "metrics": asdict(evaluate(graph, matching)),
            "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        results[name] = result
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--namespace", default="speed-dating-wave-2",
                        help="prepopulated Redis namespace (default: speed-dating-wave-2)")
    args = parser.parse_args()
    store = RedisStore(args.namespace)

    # All three algorithms operate on the same graph reconstructed from storage.
    graph = store.load_graph()
    results = compare_graph(graph)
    for name, result in results.items():
        store.save_result(name, result)

    print(json.dumps({
        "metadata": store.metadata(),
        "population": {
            "u_count": len(graph.u),
            "v_count": len(graph.v),
            "mutual_edges": len(graph.edges),
            "u_preferences": {u: graph.u_preferences[u] for u in graph.u},
            "v_preferences": {v: graph.v_preferences[v] for v in graph.v},
        },
        "results": results,
    }, indent=2))


if __name__ == "__main__":
    main()
