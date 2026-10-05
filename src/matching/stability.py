"""Matching representation and independent stability verification."""

from dataclasses import dataclass
from typing import Mapping

from graph.preferences import PreferenceGraph


@dataclass(frozen=True)
class Matching:
    u_to_v: Mapping[str, str | None]
    v_to_u: Mapping[str, str | None]

    @classmethod
    def from_pairs(cls, graph: PreferenceGraph, pairs: list[tuple[str, str]]) -> "Matching":
        u_to_v: dict[str, str | None] = {u: None for u in graph.u}
        v_to_u: dict[str, str | None] = {v: None for v in graph.v}
        for u, v in pairs:
            if not graph.mutually_acceptable(u, v):
                raise ValueError(f"Invalid matching edge: ({u}, {v})")
            if u_to_v[u] is not None or v_to_u[v] is not None:
                raise ValueError("Matching must be one-to-one")
            u_to_v[u], v_to_u[v] = v, u
        return cls(u_to_v, v_to_u)

    def pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple((u, v) for u, v in self.u_to_v.items() if v is not None)


def validate_matching(graph: PreferenceGraph, matching: Matching) -> None:
    if set(matching.u_to_v) != set(graph.u) or set(matching.v_to_u) != set(graph.v):
        raise ValueError("Matching must specify every participant, including unmatched ones")
    for u, v in matching.u_to_v.items():
        if v is not None and (
            not graph.mutually_acceptable(u, v) or matching.v_to_u[v] != u
        ):
            raise ValueError("Matching contains an ineligible or nonreciprocal pair")
    for v, u in matching.v_to_u.items():
        if u is not None and matching.u_to_v.get(u) != v:
            raise ValueError("Matching contains a nonreciprocal pair")


def blocking_pairs(graph: PreferenceGraph, matching: Matching) -> list[tuple[str, str]]:
    validate_matching(graph, matching)
    blocked: list[tuple[str, str]] = []
    for u, v in graph.edges:
        current_v = matching.u_to_v[u]
        current_u = matching.v_to_u[v]
        u_prefers = current_v is None or graph.u_ranks[u][v] < graph.u_ranks[u][current_v]
        v_prefers = current_u is None or graph.v_ranks[v][u] < graph.v_ranks[v][current_u]
        if u_prefers and v_prefers:
            blocked.append((u, v))
    return blocked


def is_stable(graph: PreferenceGraph, matching: Matching) -> bool:
    return not blocking_pairs(graph, matching)
