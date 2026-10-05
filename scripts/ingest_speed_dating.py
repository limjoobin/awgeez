"""Preprocess one or all speed-dating waves into Redis preference sorted sets."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datasets.speed_dating import available_waves, preprocess_speed_dating_wave
from storage.redis_store import RedisStore


DEFAULT_CSV = (
    Path(__file__).resolve().parents[1]
    / "data" / "speed-dating-experiment" / "Speed Dating Data.csv"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--wave", type=int)
    selection.add_argument("--all-waves", action="store_true")
    parser.add_argument("--data-path", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--namespace", help="custom namespace for one wave")
    args = parser.parse_args()
    if args.all_waves and args.namespace:
        parser.error("--namespace can only be used with --wave")

    waves = available_waves(args.data_path) if args.all_waves else [args.wave]
    reports = []
    for wave in waves:
        graph, report, scores = preprocess_speed_dating_wave(args.data_path, wave)
        namespace = args.namespace or f"speed-dating-wave-{wave}"
        store = RedisStore(namespace)
        store.replace_graph(graph, {
            "source": "columbia-speed-dating",
            "csv_path": str(args.data_path.resolve()),
            "wave": wave,
            "preprocessing": "all rated dates; like descending; weighted attributes for complete like ties; iid fallback",
            "report": asdict(report),
        }, ranking_scores=scores.as_store_mapping())
        # Verify that the stored graph can be rebuilt before reporting success.
        reloaded = store.load_graph()
        if (reloaded.u != graph.u or reloaded.v != graph.v
                or dict(reloaded.u_preferences) != dict(graph.u_preferences)
                or dict(reloaded.v_preferences) != dict(graph.v_preferences)):
            raise RuntimeError(f"Redis round-trip changed wave {wave}")
        reports.append({"namespace": namespace, **asdict(report)})
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
