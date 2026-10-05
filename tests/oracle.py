"""Small exhaustive reference independent of the CP-SAT formulation."""

from graph.preferences import PreferenceGraph
from matching.stability import Matching, is_stable
from evaluation.metrics import evaluate


def exhaustive_best(graph: PreferenceGraph) -> tuple[tuple[int, int], Matching]:
    best: tuple[tuple[int, int], Matching] | None = None

    def visit(index: int, used_v: set[str], chosen: list[tuple[str, str]]) -> None:
        nonlocal best
        if index == len(graph.u):
            matching = Matching.from_pairs(graph, chosen)
            if is_stable(graph, matching):
                metrics = evaluate(graph, matching)
                score = (metrics.maximum_regret, metrics.total_regret)
                if best is None or score < best[0]:
                    best = (score, matching)
            return
        u = graph.u[index]
        visit(index + 1, used_v, chosen)
        for v in graph.v:
            if v not in used_v and graph.mutually_acceptable(u, v):
                used_v.add(v)
                chosen.append((u, v))
                visit(index + 1, used_v, chosen)
                chosen.pop()
                used_v.remove(v)

    visit(0, set(), [])
    assert best is not None
    return best
