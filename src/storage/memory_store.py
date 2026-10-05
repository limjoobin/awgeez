"""In-memory preference and result store for tests and local experiments."""

import json
from collections.abc import Mapping
from typing import Any

from graph.preferences import PreferenceGraph


class MemoryStore:
    def __init__(self) -> None:
        self._graph: PreferenceGraph | None = None
        self._metadata: dict[str, Any] = {}
        self._results: dict[str, dict[str, Any]] = {}

    def replace_graph(
        self, graph: PreferenceGraph, metadata: Mapping[str, Any] | None = None
    ) -> None:
        self._graph = PreferenceGraph(graph.u_preferences, graph.v_preferences)
        self._metadata = json.loads(json.dumps(metadata or {}, allow_nan=False))
        self._results.clear()

    def load_graph(self) -> PreferenceGraph:
        if self._graph is None:
            raise KeyError("No preference graph has been stored")
        return PreferenceGraph(self._graph.u_preferences, self._graph.v_preferences)

    def metadata(self) -> dict[str, Any]:
        self.load_graph()
        return json.loads(json.dumps(self._metadata))

    def _preferences(self, participant: str) -> tuple[str, ...]:
        graph = self.load_graph()
        if participant in graph.u_preferences:
            return graph.u_preferences[participant]
        if participant in graph.v_preferences:
            return graph.v_preferences[participant]
        raise KeyError(participant)

    def ranked(
        self, participant: str, *, top_k: int | None = None,
        max_rank: int | None = None,
    ) -> list[tuple[str, int]]:
        if top_k is not None and top_k < 0:
            raise ValueError("top_k must be nonnegative")
        choices = list(enumerate(self._preferences(participant), 1))
        if max_rank is not None:
            choices = [(rank, candidate) for rank, candidate in choices if rank <= max_rank]
        if top_k is not None:
            choices = choices[:top_k]
        return [(candidate, rank) for rank, candidate in choices]

    def pair_rank(self, participant: str, candidate: str) -> int | None:
        return next(
            (rank for partner, rank in self.ranked(participant) if partner == candidate),
            None,
        )

    def save_result(self, name: str, result: Mapping[str, Any]) -> None:
        self.load_graph()
        self._results[name] = json.loads(json.dumps(result, allow_nan=False))

    def load_result(self, name: str) -> dict[str, Any] | None:
        result = self._results.get(name)
        return json.loads(json.dumps(result)) if result is not None else None

    def result_names(self) -> list[str]:
        return sorted(self._results)
