"""Mark 0/10 body items in the original skill."""

import argparse
import json
from pathlib import Path
import re

from .items import split_document
from .judge import prior_counts

MARK = "**[FOCUS]**"
NOTE = (
    "> **Items marked `[FOCUS]`.** Pay particular attention to the items marked `[FOCUS]` below. "
    "When you plan the corresponding steps, carry their specific procedures, tools, parameters, "
    "conditions, and exceptions into your plan as written, instead of simplifying them to a "
    "generic approach."
)
BODY_TYPES = {"list entry", "paragraph", "code block", "table"}
LIST = re.compile(r"^(\s*(?:>\s*)*)([-*+]|\d+[.)])(\s+)(\[[ xX]\]\s+)?")


def mark(original, items, coverage):
    newline = "\r\n" if "\r\n" in original else "\n"
    front, body = split_document(original)
    first = re.search(r"\S", body)
    position = len(front) + (first.start() if first else 0)
    title = re.match(r"#[ \t]+[^\r\n]*(?:\r?\n|$)", original[position:])
    if title:
        position += title.end()
    edits = [(position, newline + NOTE + newline + newline)]
    for item in items:
        if item["type"] not in BODY_TYPES or coverage[item["id"]] != 0:
            continue
        position = item["start"]
        if original[position:item["end"]] != item["text"]:
            raise ValueError(f"Original item {item['id']} no longer matches.")
        marker = LIST.match(item["text"]) if item["type"] == "list entry" else None
        if marker:
            edits.append((position + marker.end(), MARK + " "))
        else:
            indentation = re.match(r"[ \t]*", item["text"]).group()
            edits.append((position, indentation + MARK + newline + newline))
    # Insert only. Removing these insertions recovers the original bytes.
    result = original
    for position, text in reversed(sorted(edits, key=lambda edit: edit[0])):
        result = result[:position] + text + result[position:]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    args = parser.parse_args()
    originals = sorted(args.runs.glob("*/original.md"))
    if not originals:
        parser.error(f"No skills in {args.runs}")
    for original in originals:
        run = original.parent
        items = json.loads((run / "items.json").read_text())
        text = mark(original.read_bytes().decode("utf-8"), items, prior_counts(run, items))
        destination = run / "skilldiff.md"
        destination.write_bytes(text.encode("utf-8"))
        print(destination)


if __name__ == "__main__":
    main()
