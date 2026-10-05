"""Namespaced Redis storage; preference lists are sorted sets of rank scores."""

import json
import os
import re
from collections.abc import Mapping
from typing import Any

import redis

from graph.preferences import PreferenceGraph


class RedisStore:
    def __init__(
        self,
        namespace: str,
        *,
        url: str | None = None,
        client: redis.Redis | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", namespace):
            raise ValueError("namespace must contain only letters, digits, '.', '_', or '-'")
        self.prefix = f"mm:{namespace}"
        self.client = client or redis.Redis.from_url(
            url or os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"),
            decode_responses=True, socket_timeout=10,
        )

    def _key(self, suffix: str) -> str:
        return f"{self.prefix}:{suffix}"

    def _participant_ids(self) -> tuple[list[str], list[str]]:
        return (
            self.client.zrange(self._key("participants:u"), 0, -1),
            self.client.zrange(self._key("participants:v"), 0, -1),
        )

    def _known_keys(self) -> list[str]:
        u, v = self._participant_ids()
        names = self.client.smembers(self._key("result_names"))
        return [
            self._key("meta"),
            self._key("participants:u"),
            self._key("participants:v"),
            self._key("result_names"),
            *(self._key(f"prefs:{person}") for person in (*u, *v)),
            *(self._key(f"scores:{kind}:{person}")
              for kind in ("like", "attributes") for person in (*u, *v)),
            *(self._key(f"results:{name}") for name in names),
        ]

    def clear_namespace(self) -> None:
        self.client.delete(*self._known_keys())

    def replace_graph(
        self, graph: PreferenceGraph, metadata: Mapping[str, Any] | None = None,
        ranking_scores: Mapping[str, Mapping[str, Mapping[str, float]]] | None = None,
    ) -> None:
        # Delete only keys registered under this namespace, never the Redis DB.
        if ranking_scores is not None:
            if set(ranking_scores) - {"like", "attributes"}:
                raise ValueError("Unsupported ranking score kind")
            for kind, by_person in ranking_scores.items():
                for person, scores in by_person.items():
                    preferences = graph.u_preferences.get(person)
                    if preferences is None:
                        preferences = graph.v_preferences.get(person)
                    if preferences is None or not set(scores) <= set(preferences):
                        raise ValueError(f"Invalid {kind} score candidates for {person}")
        old_keys = self._known_keys()
        with self.client.pipeline(transaction=True) as pipe:
            pipe.delete(*old_keys)
            pipe.set(self._key("meta"), json.dumps(metadata or {}, allow_nan=False))
            for side, people, preferences in (
                ("u", graph.u, graph.u_preferences),
                ("v", graph.v, graph.v_preferences),
            ):
                if people:
                    pipe.zadd(
                        self._key(f"participants:{side}"),
                        {person: index for index, person in enumerate(people, 1)},
                    )
                for person in people:
                    if preferences[person]:
                        pipe.zadd(
                            self._key(f"prefs:{person}"),
                            {candidate: rank for rank, candidate in enumerate(preferences[person], 1)},
                        )
            for kind, by_person in (ranking_scores or {}).items():
                for person, scores in by_person.items():
                    if scores:
                        pipe.zadd(self._key(f"scores:{kind}:{person}"), dict(scores))
            pipe.execute()

    def load_graph(self) -> PreferenceGraph:
        if not self.client.exists(self._key("meta")):
            raise KeyError("No preference graph has been stored")
        u, v = self._participant_ids()
        u_preferences = {person: [candidate for candidate, _ in self.ranked(person)] for person in u}
        v_preferences = {person: [candidate for candidate, _ in self.ranked(person)] for person in v}
        return PreferenceGraph(u_preferences, v_preferences)

    def metadata(self) -> dict[str, Any]:
        raw = self.client.get(self._key("meta"))
        if raw is None:
            raise KeyError("No preference graph has been stored")
        return json.loads(raw)

    def _require_participant(self, participant: str) -> None:
        if (self.client.zscore(self._key("participants:u"), participant) is None
                and self.client.zscore(self._key("participants:v"), participant) is None):
            raise KeyError(participant)

    def ranked(
        self, participant: str, *, top_k: int | None = None,
        max_rank: int | None = None,
    ) -> list[tuple[str, int]]:
        if top_k is not None and top_k < 0:
            raise ValueError("top_k must be nonnegative")
        self._require_participant(participant)
        key = self._key(f"prefs:{participant}")
        if max_rank is None:
            stop = top_k - 1 if top_k is not None else -1
            entries = self.client.zrange(key, 0, stop, withscores=True) if top_k != 0 else []
        else:
            entries = self.client.zrangebyscore(
                key, "-inf", max_rank,
                start=0 if top_k is not None else None,
                num=top_k if top_k is not None else None,
                withscores=True,
            ) if top_k != 0 else []
        result = [(candidate, int(score)) for candidate, score in entries]
        if any(score != index for index, (_, score) in enumerate(result, 1)) and max_rank is None:
            raise ValueError(f"Non-contiguous preference ranks for {participant}")
        return result

    def pair_rank(self, participant: str, candidate: str) -> int | None:
        self._require_participant(participant)
        score = self.client.zscore(self._key(f"prefs:{participant}"), candidate)
        return int(score) if score is not None else None

    def pair_scores(self, participant: str, candidate: str) -> dict[str, float | None]:
        """Return stored raw liking and weighted attribute score, when present."""
        self._require_participant(participant)
        return {
            kind: self.client.zscore(self._key(f"scores:{kind}:{participant}"), candidate)
            for kind in ("like", "attributes")
        }

    def save_result(self, name: str, result: Mapping[str, Any]) -> None:
        self.metadata()
        if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
            raise ValueError("result name contains unsupported characters")
        with self.client.pipeline(transaction=True) as pipe:
            pipe.set(self._key(f"results:{name}"), json.dumps(result, allow_nan=False))
            pipe.sadd(self._key("result_names"), name)
            pipe.execute()

    def load_result(self, name: str) -> dict[str, Any] | None:
        raw = self.client.get(self._key(f"results:{name}"))
        return json.loads(raw) if raw is not None else None

    def result_names(self) -> list[str]:
        return sorted(self.client.smembers(self._key("result_names")))
