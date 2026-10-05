"""Small, fixed preference graphs for matching tests."""

from graph.preferences import PreferenceGraph


SMALL_GRAPHS = (
    (
        "balanced complete",
        PreferenceGraph(
            {
                "u1": ["v2", "v3", "v1"],
                "u2": ["v3", "v1", "v2"],
                "u3": ["v1", "v3", "v2"],
            },
            {
                "v1": ["u1", "u2", "u3"],
                "v2": ["u2", "u1", "u3"],
                "v3": ["u3", "u1", "u2"],
            },
        ),
    ),
    (
        "more participants on u side",
        PreferenceGraph(
            {
                "u1": ["v1", "v2"],
                "u2": ["v2"],
                "u3": ["v1"],
                "u4": [],
            },
            {
                "v1": ["u3", "u1"],
                "v2": ["u1", "u2"],
                "v3": ["u1"],
            },
        ),
    ),
    (
        "more participants on v side",
        PreferenceGraph(
            {
                "u1": ["v3", "v2", "v1"],
                "u2": ["v1", "v4"],
                "u3": ["v5", "v2", "v4"],
            },
            {
                "v1": ["u2", "u1"],
                "v2": ["u3", "u1"],
                "v3": ["u1"],
                "v4": ["u2", "u3"],
                "v5": ["u3", "u2"],
            },
        ),
    ),
    ("no eligible pairs", PreferenceGraph({"u1": []}, {"v1": []})),
)
