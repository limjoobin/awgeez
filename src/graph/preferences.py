"""Generic, two-sided preference graph with mutually acceptable edges."""

from collections.abc import Mapping, Sequence
from types import MappingProxyType


class PreferenceGraph:
    def __init__(
        self,
        u_preferences: Mapping[str, Sequence[str]],
        v_preferences: Mapping[str, Sequence[str]],
    ) -> None:
        self.u = tuple(u_preferences)
        self.v = tuple(v_preferences)
        if set(self.u) & set(self.v):
            raise ValueError("Participant IDs must be unique across both sides")
        self.u_preferences = self._validate(u_preferences, set(self.v))
        self.v_preferences = self._validate(v_preferences, set(self.u))
        self.u_ranks = MappingProxyType({
            u: MappingProxyType({v: i for i, v in enumerate(prefs, 1)})
            for u, prefs in self.u_preferences.items()
        })
        self.v_ranks = MappingProxyType({
            v: MappingProxyType({u: i for i, u in enumerate(prefs, 1)})
            for v, prefs in self.v_preferences.items()
        })
        self.edges = tuple(
            (u, v)
            for u in self.u
            for v in self.u_preferences[u]
            if u in self.v_ranks[v]
        )

    @staticmethod
    def _validate(
        preferences: Mapping[str, Sequence[str]], other_side: set[str]
    ) -> Mapping[str, tuple[str, ...]]:
        validated: dict[str, tuple[str, ...]] = {}
        for participant, candidates in preferences.items():
            if not isinstance(participant, str) or not participant:
                raise ValueError("Participant IDs must be nonempty strings")
            choices = tuple(candidates)
            if any(not isinstance(candidate, str) or candidate not in other_side for candidate in choices):
                raise ValueError(f"Unknown candidate in preferences for {participant}")
            if len(choices) != len(set(choices)):
                raise ValueError(f"Duplicate candidate in preferences for {participant}")
            validated[participant] = choices
        return MappingProxyType(validated)

    def mutually_acceptable(self, u: str, v: str) -> bool:
        return u in self.u_ranks and v in self.v_ranks and v in self.u_ranks[u] and u in self.v_ranks[v]

    def ranks(self, u: str, v: str) -> tuple[int, int]:
        if not self.mutually_acceptable(u, v):
            raise ValueError(f"{u} and {v} are not mutually acceptable")
        return self.u_ranks[u][v], self.v_ranks[v][u]
