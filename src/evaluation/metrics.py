"""Regret and stability metrics for a complete matching assignment."""

from dataclasses import dataclass
from statistics import mean, median
from typing import Mapping

from graph.preferences import PreferenceGraph
from matching.stability import Matching, blocking_pairs


@dataclass(frozen=True)
class Assignment:
    partner: str | None
    regret: int | None


@dataclass(frozen=True)
class Metrics:
    maximum_regret: int | None
    total_regret: int
    mean_regret: float | None
    median_regret: float | None
    regret_distribution: Mapping[int, int]
    matched_participants: int
    unmatched_participants: int
    blocking_pair_count: int
    assignments: Mapping[str, Assignment]


def evaluate(graph: PreferenceGraph, matching: Matching) -> Metrics:
    blocked = blocking_pairs(graph, matching)
    assignments: dict[str, Assignment] = {}
    for u in graph.u:
        partner = matching.u_to_v[u]
        assignments[u] = Assignment(
            partner, graph.u_ranks[u][partner] if partner is not None else None
        )
    for v in graph.v:
        partner = matching.v_to_u[v]
        assignments[v] = Assignment(
            partner, graph.v_ranks[v][partner] if partner is not None else None
        )
    regrets = [entry.regret for entry in assignments.values() if entry.regret is not None]
    distribution: dict[int, int] = {}
    for regret in regrets:
        distribution[regret] = distribution.get(regret, 0) + 1
    unmatched = sum(entry.partner is None for entry in assignments.values())
    return Metrics(
        maximum_regret=max(regrets, default=None),
        total_regret=sum(regrets),
        mean_regret=mean(regrets) if regrets else None,
        median_regret=median(regrets) if regrets else None,
        regret_distribution=dict(sorted(distribution.items())),
        matched_participants=len(assignments) - unmatched,
        unmatched_participants=unmatched,
        blocking_pair_count=len(blocked),
        assignments=assignments,
    )
