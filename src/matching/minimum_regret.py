"""Exact lexicographic minimax-regret stable matching with CP-SAT."""

from ortools.sat.python import cp_model

from graph.preferences import PreferenceGraph
from .stability import Matching, is_stable


def minimum_regret(graph: PreferenceGraph) -> Matching:
    """Minimize maximum matched rank, then total matched rank, over stable matchings."""

    model = cp_model.CpModel()
    x = {(u, v): model.NewBoolVar(f"pair_{u}_{v}") for u, v in graph.edges}
    by_u = {u: [x[u, v] for v in graph.v if (u, v) in x] for u in graph.u}
    by_v = {v: [x[u, v] for u in graph.u if (u, v) in x] for v in graph.v}
    for incident in (*by_u.values(), *by_v.values()):
        model.Add(sum(incident) <= 1)

    # A mutually acceptable edge must be beaten by at least one endpoint's
    # current assignment. This checks preferences from the original graph.
    for u, v in graph.edges:
        u_rank, v_rank = graph.ranks(u, v)
        u_at_least_as_good = [
            x[u, other_v]
            for other_v in graph.u_preferences[u]
            if (u, other_v) in x and graph.u_ranks[u][other_v] <= u_rank
        ]
        v_at_least_as_good = [
            x[other_u, v]
            for other_u in graph.v_preferences[v]
            if (other_u, v) in x and graph.v_ranks[v][other_u] <= v_rank
        ]
        model.Add(sum(u_at_least_as_good) + sum(v_at_least_as_good) >= 1)

    possible_regrets = [rank for u, v in graph.edges for rank in graph.ranks(u, v)]
    maximum = model.NewIntVar(0, max(possible_regrets, default=0), "maximum_regret")
    total_terms = []
    for (u, v), selected in x.items():
        u_rank, v_rank = graph.ranks(u, v)
        model.Add(maximum >= u_rank * selected)
        model.Add(maximum >= v_rank * selected)
        total_terms.append((u_rank + v_rank) * selected)

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    model.Minimize(maximum)
    if solver.Solve(model) != cp_model.OPTIMAL:
        raise RuntimeError("CP-SAT did not prove the minimum maximum regret")
    optimal_maximum = solver.Value(maximum)
    model.Add(maximum == optimal_maximum)
    model.Minimize(sum(total_terms))
    if solver.Solve(model) != cp_model.OPTIMAL:
        raise RuntimeError("CP-SAT did not prove the minimum total regret")

    matching = Matching.from_pairs(
        graph, [edge for edge, selected in x.items() if solver.BooleanValue(selected)]
    )
    if not is_stable(graph, matching):
        raise RuntimeError("Optimizer produced an unstable matching")
    return matching
