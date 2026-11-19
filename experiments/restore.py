"""Restore lost items to a common base constructed from the round-30 skill."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from .judge import LOST, prior_counts, read_labels
from .model import add_model_arguments, complete, read_json_response


def build(rewritten, items, coverage, locations):
    """Return a common base and the three restored versions."""
    by_id = {item["id"]: item for item in items}
    if len(locations) != len(items) or {row["id"] for row in locations} != set(by_id):
        raise ValueError("Each lost item must have exactly one location.")
    lines = rewritten.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    removed = set()
    insertions = defaultdict(list)
    for row in locations:
        after = row["after_line"]
        if after is None:
            after = len(lines)
        if not isinstance(after, int) or not 0 <= after <= len(lines):
            raise ValueError(f"Invalid insertion line for {row['id']}")
        insertions[offsets[after]].append(by_id[row["id"]])
        for passage in row["remove"]:
            quote = passage["text"]
            first, last = passage["start_line"], passage["end_line"]
            if not isinstance(quote, str) or not quote or not 1 <= first <= last <= len(lines):
                raise ValueError(f"Invalid removal span for {row['id']}")
            window = rewritten[offsets[first - 1]:offsets[last]]
            if window.count(quote) != 1:
                raise ValueError(f"Removal text for {row['id']} must match once in its line span.")
            start = offsets[first - 1] + window.index(quote)
            removed.update(range(start, start + len(quote)))
    base = "".join(char for index, char in enumerate(rewritten) if index not in removed)
    versions = {}
    for condition in ("outside", "other", "all"):
        chunks = []
        for position in range(len(rewritten) + 1):
            selected = sorted(insertions.get(position, []), key=lambda item: item["start"])
            for item in selected:
                outside = coverage[item["id"]] == 0
                include = condition == "all" or (condition == "outside") == outside
                if include:
                    prefix = "" if item["type"] == "front matter" and position == 0 else "\n\n"
                    chunks.append(prefix + item["text"] + "\n\n")
            if position < len(rewritten) and position not in removed:
                chunks.append(rewritten[position])
        versions[condition] = "".join(chunks)
    return base, versions


def restore_run(run, backend, model):
    items = json.loads((run / "items.json").read_text())
    coverage = prior_counts(run, items)
    labels = read_labels(run, "round", 30)
    lost = [item for item in items if labels[item["id"]] in LOST]
    rewritten = (run / "chain" / "30.md").read_bytes().decode("utf-8")
    numbered = "".join(f"{index}: {line}" for index, line in enumerate(rewritten.splitlines(keepends=True), 1))
    prompt = (
        "Locate each lost original item in the round-30 document. Identify the exact "
        "sentences or passages carrying a weakened or changed version for removal. "
        "Select an insertion point corresponding to the item's original position. "
        "Use after_line 0 for the beginning and null when no position can be found. "
        "Return one JSON object per item in an array, with id, after_line, and remove. "
        "remove is a list of objects with start_line, end_line and text copied exactly "
        "from the numbered document without its line-number prefix. Use an empty list "
        "when the document no longer carries the item.\nLOST ORIGINAL ITEMS\n"
        + json.dumps(lost, ensure_ascii=False) + "\nROUND-30 DOCUMENT\n" + numbered
    )
    fingerprint = hashlib.sha256((backend + model + prompt).encode()).hexdigest()
    location_file = run / "locations.json"
    if location_file.exists():
        saved = json.loads(location_file.read_text())
        if saved["input_sha256"] != fingerprint:
            raise ValueError(f"Location inputs changed in {run}. Move locations.json before rerunning.")
        locations = saved["locations"]
    else:
        locations = read_json_response(complete(prompt, backend, model)) if lost else []
    base, versions = build(rewritten, lost, coverage, locations)
    location_file.write_text(json.dumps({
        "input_sha256": fingerprint, "locations": locations,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output = run / "restored"
    output.mkdir(exist_ok=True)
    (output / "base.md").write_bytes(base.encode("utf-8"))
    for condition, text in versions.items():
        destination = output / (condition + ".md")
        destination.write_bytes(text.encode("utf-8"))
        print(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    add_model_arguments(parser)
    args = parser.parse_args()
    originals = sorted(args.runs.glob("*/original.md"))
    if not originals:
        parser.error(f"No skills in {args.runs}")
    for original in originals:
        restore_run(original.parent, args.backend, args.model)


if __name__ == "__main__":
    main()
