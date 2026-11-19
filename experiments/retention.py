"""Measure item retention by draft coverage after rounds 1 and 30."""

import argparse
import json
from pathlib import Path

from .judge import KEPT, LOST, prior_counts, read_labels

GROUPS = {"0": (0, 0), "1–3": (1, 3), "4–6": (4, 6), "7–9": (7, 9), "10": (10, 10)}


def summarize(runs, repeats):
    originals = sorted(runs.glob("*/original.md"))
    if not originals:
        raise ValueError(f"No skills in {runs}")
    counts = {index: [[0, 0] for _ in range(11)] for index in (1, 30)}
    for original in originals:
        run = original.parent
        items = json.loads((run / "items.json").read_text())
        coverage = prior_counts(run, items)
        chains = [run] + [folder / run.name for folder in repeats]
        for chain in chains:
            for index in counts:
                labels = read_labels(chain, "round", index)
                for item in items:
                    value = labels[item["id"]]
                    group = counts[index][coverage[item["id"]]]
                    group[0] += value in KEPT
                    group[1] += value in KEPT | LOST
    result = {}
    for index, per_count in counts.items():
        result[index] = {}
        for name, (low, high) in GROUPS.items():
            kept = sum(row[0] for row in per_count[low:high + 1])
            total = sum(row[1] for row in per_count[low:high + 1])
            result[index][name] = {
                "kept": kept, "total": total,
                "retention_pct": 100 * kept / total if total else None,
            }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--repeat", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.runs, args.repeat)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
