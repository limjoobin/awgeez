"""Columbia speed-dating CSV adapter; algorithms see only PreferenceGraph."""

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from graph.preferences import PreferenceGraph


ATTRIBUTES = ("attr", "sinc", "intel", "fun", "amb", "shar")
WEIGHT_COLUMNS = ("attr1_1", "sinc1_1", "intel1_1", "fun1_1", "amb1_1", "shar1_1")
REQUIRED_COLUMNS = {
    "wave", "iid", "id", "gender", "pid", "partner", "dec", "like",
    *ATTRIBUTES, *WEIGHT_COLUMNS,
}


@dataclass(frozen=True)
class IngestionReport:
    wave: int
    rows: int
    u_participants: int
    v_participants: int
    yes_decisions: int
    rated_entries: int
    mutual_edges: int
    missing_partner_ids: int
    unresolved_partner_rows: int
    missing_like: int
    like_tie_groups: int
    attribute_resolved_groups: int
    attribute_fallback_groups: int


@dataclass(frozen=True)
class RankingScores:
    """Directed scores used to construct each participant's ranking."""

    like: dict[str, dict[str, float]]
    attributes: dict[str, dict[str, float]]

    def as_store_mapping(self) -> dict[str, dict[str, dict[str, float]]]:
        return {"like": self.like, "attributes": self.attributes}


def _number(raw: str, label: str) -> Decimal | None:
    if not raw.strip():
        return None
    try:
        value = Decimal(raw.strip())
    except InvalidOperation as exc:
        raise ValueError(f"Invalid {label}: {raw!r}") from exc
    if not value.is_finite():
        raise ValueError(f"Non-finite {label}")
    return value


def available_waves(path: str | Path) -> list[int]:
    with open(path, encoding="cp1252", newline="") as stream:
        rows = csv.DictReader(stream)
        if rows.fieldnames is None or "wave" not in rows.fieldnames:
            raise ValueError("CSV is missing the wave column")
        return sorted({int(row["wave"]) for row in rows if row["wave"].strip()})


def preprocess_speed_dating_wave(
    path: str | Path, wave: int
) -> tuple[PreferenceGraph, IngestionReport, RankingScores]:
    """Rank rated dates by like, resolving complete ties with weighted attributes."""
    with open(path, encoding="cp1252", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not REQUIRED_COLUMNS <= set(reader.fieldnames):
            missing = REQUIRED_COLUMNS - set(reader.fieldnames or ())
            raise ValueError(f"CSV is missing required columns: {sorted(missing)}")
        rows = [row for row in reader if row["wave"].strip() == str(wave)]
    if not rows:
        raise ValueError(f"Wave {wave} is absent from the CSV")

    # iid is the dataset-wide ID; id and partner are IDs local to a wave.
    side_by_iid: dict[str, str] = {}
    local_to_iid: dict[tuple[str, str], str] = {}
    first_row_by_iid: dict[str, dict[str, str]] = {}
    for row in rows:
        iid, side, local_id = (
            row["iid"].strip(), row["gender"].strip(), row["id"].strip()
        )
        if not iid or side not in ("0", "1"):
            raise ValueError("A wave row has no participant ID or valid gender side")
        if iid in side_by_iid and side_by_iid[iid] != side:
            raise ValueError(f"Conflicting sides for participant {iid}")
        side_by_iid[iid] = side
        first_row_by_iid.setdefault(iid, row)
        if local_id:
            key = (side, local_id)
            if key in local_to_iid and local_to_iid[key] != iid:
                raise ValueError(f"Ambiguous wave-local participant ID {key}")
            local_to_iid[key] = iid

    def participant_id(iid: str) -> str:
        return ("u" if side_by_iid[iid] == "0" else "v") + iid

    members = {
        "0": sorted((iid for iid, side in side_by_iid.items() if side == "0"), key=int),
        "1": sorted((iid for iid, side in side_by_iid.items() if side == "1"), key=int),
    }
    people = [participant_id(iid) for iid in (*members["0"], *members["1"])]
    weights: dict[str, tuple[Decimal, ...] | None] = {}
    for iid, row in first_row_by_iid.items():
        values = tuple(_number(row[column], column) for column in WEIGHT_COLUMNS)
        if any(value is None for value in values):
            weights[participant_id(iid)] = None
        else:
            complete = tuple(value for value in values if value is not None)
            if any(value < 0 for value in complete):
                raise ValueError(f"Negative attribute importance for {iid}")
            total = sum(complete)
            weights[participant_id(iid)] = (
                tuple(value / total for value in complete) if total else None
            )

    likes: dict[str, dict[str, Decimal]] = {person: {} for person in people}
    attribute_scores: dict[str, dict[str, Decimal]] = {person: {} for person in people}
    yes_decisions = missing_partner_ids = unresolved_partner_rows = missing_like = 0
    for row in rows:
        source_iid = row["iid"].strip()
        source_side = side_by_iid[source_iid]
        decision = row["dec"].strip()
        if decision not in ("0", "1"):
            raise ValueError(f"Invalid decision value for {source_iid}: {decision!r}")
        yes_decisions += decision == "1"
        like = _number(row["like"], "like score")
        missing_like += like is None
        partner_iid = row["pid"].strip()
        if not partner_iid:
            missing_partner_ids += 1
            other_side = "1" if source_side == "0" else "0"
            partner_iid = local_to_iid.get((other_side, row["partner"].strip()), "")
        if (not partner_iid or partner_iid not in side_by_iid
                or side_by_iid[partner_iid] == source_side):
            unresolved_partner_rows += 1
            continue
        if like is None:
            continue
        source = participant_id(source_iid)
        partner = participant_id(partner_iid)
        if partner in likes[source]:
            raise ValueError(f"Duplicate date row for {source} and {partner}")
        likes[source][partner] = like
        importance = weights[source]
        if importance is not None:
            ratings = tuple(_number(row[column], column) for column in ATTRIBUTES)
            if all(rating is not None for rating in ratings):
                attribute_scores[source][partner] = sum(
                    weight * rating
                    for weight, rating in zip(importance, ratings)
                    if rating is not None
                )

    like_tie_groups = attribute_resolved_groups = attribute_fallback_groups = 0

    def ranked_list(person: str) -> list[str]:
        nonlocal like_tie_groups, attribute_resolved_groups, attribute_fallback_groups
        by_like: dict[Decimal, list[str]] = {}
        for candidate, score in likes[person].items():
            by_like.setdefault(score, []).append(candidate)
        ranked: list[str] = []
        for score in sorted(by_like, reverse=True):
            group = by_like[score]
            if len(group) > 1:
                like_tie_groups += 1
                # A partially scored group falls back together, keeping the
                # ordering deterministic and avoiding incomparable pairs.
                if all(candidate in attribute_scores[person] for candidate in group):
                    if len({attribute_scores[person][candidate] for candidate in group}) > 1:
                        attribute_resolved_groups += 1
                    group.sort(key=lambda candidate: (
                        -attribute_scores[person][candidate], int(candidate[1:])
                    ))
                else:
                    attribute_fallback_groups += 1
                    group.sort(key=lambda candidate: int(candidate[1:]))
            ranked.extend(group)
        return ranked

    graph = PreferenceGraph(
        {participant_id(iid): ranked_list(participant_id(iid)) for iid in members["0"]},
        {participant_id(iid): ranked_list(participant_id(iid)) for iid in members["1"]},
    )
    report = IngestionReport(
        wave=wave,
        rows=len(rows),
        u_participants=len(graph.u),
        v_participants=len(graph.v),
        yes_decisions=yes_decisions,
        rated_entries=sum(map(len, likes.values())),
        mutual_edges=len(graph.edges),
        missing_partner_ids=missing_partner_ids,
        unresolved_partner_rows=unresolved_partner_rows,
        missing_like=missing_like,
        like_tie_groups=like_tie_groups,
        attribute_resolved_groups=attribute_resolved_groups,
        attribute_fallback_groups=attribute_fallback_groups,
    )
    scores = RankingScores(
        like={person: {candidate: float(value) for candidate, value in ratings.items()}
              for person, ratings in likes.items()},
        attributes={
            person: {candidate: float(value) for candidate, value in values.items()}
            for person, values in attribute_scores.items()
        },
    )
    return graph, report, scores


def load_speed_dating_wave(path: str | Path, wave: int) -> tuple[PreferenceGraph, IngestionReport]:
    graph, report, _ = preprocess_speed_dating_wave(path, wave)
    return graph, report
