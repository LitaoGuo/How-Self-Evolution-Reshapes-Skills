"""Judge all original items against each self-written or rewritten skill."""

import argparse
import hashlib
import json
from pathlib import Path

from .items import split_items
from .model import add_model_arguments, complete, read_json_response

DRAFT_LABELS = {"SAME", "DIFF", "ABSENT"}
KEPT = {"KEPT", "REWORDED"}
LOST = {"WEAKENED", "DROPPED", "CHANGED"}
CHANGE_LABELS = KEPT | LOST | {"UNCLEAR"}
DRAFT_RULES = (
    "SAME means the candidate conveys the same content, including equivalent code. "
    "DIFF means it addresses the same point with different content. ABSENT means it "
    "does not address the point. Shared nouns, file names or numbers without the same "
    "content do not count as SAME."
)
CHANGE_RULES = (
    "KEPT means present verbatim or near-verbatim. REWORDED means the same content in "
    "different words, including equivalent code. WEAKENED means partial, optional, "
    "hedged or incomplete content. DROPPED means absent. CHANGED means different "
    "content on the same point. UNCLEAR means you cannot decide. These labels describe "
    "content retention. A change may be harmless or an improvement."
)


def judge_run(run, backend, model, drafts_only=False):
    original = (run / "original.md").read_bytes().decode("utf-8")
    items = split_items(original)
    (run / "items.json").write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    labels = run / "labels"
    labels.mkdir(exist_ok=True)
    candidates = [("draft", index, run / "drafts" / f"{index:02d}.md") for index in range(1, 11)]
    if not drafts_only:
        candidates += [("round", index, run / "chain" / f"{index:02d}.md") for index in (1, 5, 10, 30)]
    for kind, index, candidate in candidates:
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
    for kind, index, candidate in candidates:
        document = candidate.read_text(encoding="utf-8")
        rules = DRAFT_RULES if kind == "draft" else CHANGE_RULES
        prompt = (
            "Compare every original item below with the candidate skill document.\n"
            + rules + '\nReturn a JSON array with one {"id": "...", "v": "..."} per item.\n'
            + "ORIGINAL ITEMS\n" + json.dumps(items, ensure_ascii=False)
            + "\nCANDIDATE DOCUMENT\n" + document
        )
        fingerprint = hashlib.sha256((backend + model + prompt).encode()).hexdigest()
        destination = labels / f"{kind}-{index:02d}.json"
        if destination.exists():
            previous = json.loads(destination.read_text())
            if previous.get("input_sha256") == fingerprint:
                continue
        verdicts = read_json_response(complete(prompt, backend, model))
        expected = {item["id"] for item in items}
        allowed = DRAFT_LABELS if kind == "draft" else CHANGE_LABELS
        if not isinstance(verdicts, list) or len(verdicts) != len(items):
            raise ValueError(f"Incomplete judgments for {candidate}")
        if {entry["id"] for entry in verdicts} != expected or any(entry["v"] not in allowed for entry in verdicts):
            raise ValueError(f"Invalid judgments for {candidate}")
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps({
            "input_sha256": fingerprint, "model": model, "verdicts": verdicts,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(destination)
        print(destination, flush=True)


def read_labels(run, kind, index):
    records = json.loads((run / "labels" / f"{kind}-{index:02d}.json").read_text())["verdicts"]
    labels = {record["id"]: record["v"] for record in records}
    allowed = DRAFT_LABELS if kind == "draft" else CHANGE_LABELS
    if len(labels) != len(records) or not set(labels.values()) <= allowed:
        raise ValueError(f"Invalid labels in {run}, {kind} {index}")
    return labels


def prior_counts(run, items):
    drafts = [read_labels(run, "draft", index) for index in range(1, 11)]
    return {item["id"]: sum(draft[item["id"]] == "SAME" for draft in drafts) for item in items}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--drafts-only", action="store_true", help="judge the ten self-written skills for SkillDiff")
    add_model_arguments(parser)
    args = parser.parse_args()
    runs = sorted(args.runs.glob("*/original.md"))
    if not runs:
        parser.error(f"No skills in {args.runs}")
    for original in runs:
        judge_run(original.parent, args.backend, args.model, args.drafts_only)


if __name__ == "__main__":
    main()
