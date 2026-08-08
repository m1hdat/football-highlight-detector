#!/usr/bin/env python3
"""Run the integrated Spotter V2 on an existing features.npy file."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import DEVICE
from app.pipeline.spotter_v2 import load_spotter_v2, spot_events_from_feature


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", required=True)
    parser.add_argument("--output", default="predictions_spotter_v2.json")
    parser.add_argument("--device", default=DEVICE)
    args = parser.parse_args()

    bundle = load_spotter_v2(device=args.device)
    predictions = spot_events_from_feature(
        args.features,
        bundle,
        device=args.device,
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(predictions, handle, ensure_ascii=False, indent=2)

    csv_path = output.with_suffix(".csv")
    fields = [
        "time_sec",
        "fine_label",
        "display_label",
        "score",
        "event_score",
        "class_score",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field) for field in fields} for row in predictions)

    counts = {name: 0 for name in bundle.class_names}
    for prediction in predictions:
        counts[prediction["fine_label"]] += 1
    print(f"Predictions: {len(predictions)}")
    print("Class counts:", counts)
    print("JSON:", output)
    print("CSV:", csv_path)


if __name__ == "__main__":
    main()
