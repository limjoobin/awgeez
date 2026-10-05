"""Deferred acceptance with either side proposing."""

from collections import deque
from typing import Literal

from graph.preferences import PreferenceGraph
from .stability import Matching


def gale_shapley(graph: PreferenceGraph, proposer: Literal["u", "v"] = "u") -> Matching:
    if proposer not in ("u", "v"):
        raise ValueError("proposer must be 'u' or 'v'")
    proposers = graph.u if proposer == "u" else graph.v
    receivers = graph.v if proposer == "u" else graph.u
    preferences = graph.u_preferences if proposer == "u" else graph.v_preferences
    receiver_ranks = graph.v_ranks if proposer == "u" else graph.u_ranks
    next_choice = {person: 0 for person in proposers}
    held: dict[str, str | None] = {person: None for person in receivers}
    free = deque(proposers)

    while free:
        person = free.popleft()
        choices = preferences[person]
        while next_choice[person] < len(choices):
            candidate = choices[next_choice[person]]
            next_choice[person] += 1
            if person not in receiver_ranks[candidate]:
                continue
            incumbent = held[candidate]
            if incumbent is None or receiver_ranks[candidate][person] < receiver_ranks[candidate][incumbent]:
                held[candidate] = person
                if incumbent is not None:
                    free.append(incumbent)
                break

    pairs = [(person, receiver) if proposer == "u" else (receiver, person)
             for receiver, person in held.items() if person is not None]
    return Matching.from_pairs(graph, pairs)
