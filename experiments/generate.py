"""Generate thirty rewrites and ten topic-only drafts for each original skill."""

import argparse
import json
from pathlib import Path
import re

from .model import add_model_arguments, complete

OUTPUT_RULE = (
    "Output ONLY the resulting document, with no preamble, no commentary, and no "
    "code fence around the whole thing. Write it in the same language as the input."
)
WORD = re.compile(r"[A-Za-z0-9_\-./]+")


def generate(skill, topic, output, backend, model, stage):
    original = skill.read_text(encoding="utf-8")
    settings = {"original": original, "topic": topic, "backend": backend, "model": model}
    manifest = output / "input.json"
    if manifest.exists() and json.loads(manifest.read_text()) != settings:
        raise ValueError(f"Inputs changed in {output}. Choose a new output directory.")
    output.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "original.md").write_bytes(skill.read_bytes())
    budget = len(WORD.findall(original))
    length = f"Length: about {budget} words.\n\n"
    stages = ("chain", "drafts") if stage == "all" else (stage,)
    for kind in stages:
        folder = output / kind
        folder.mkdir(exist_ok=True)
        previous = original
        count = 30 if kind == "chain" else 10
        for index in range(1, count + 1):
            destination = folder / f"{index:02d}.md"
            if destination.exists():
                previous = destination.read_text(encoding="utf-8")
                continue
            if kind == "chain":
                prompt = (
                    f'On the topic "{topic}", identify the problems in the skill document '
                    "below and improve it.\n\n" + length + OUTPUT_RULE
                    + "\n\n---BEGIN DOCUMENT---\n" + previous + "\n---END DOCUMENT---\n"
                )
            else:
                prompt = f'On the topic "{topic}", write a skill document for an AI agent.\n\n'
                prompt += length + OUTPUT_RULE
            previous = complete(prompt, backend, model)
            temporary = destination.with_suffix(".tmp")
            temporary.write_text(previous + "\n", encoding="utf-8")
            temporary.replace(destination)
            print(destination, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", type=Path, required=True, help="directory containing <id>/SKILL.md")
    parser.add_argument("--topics", type=Path, required=True, help="directory containing <id>.txt")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--stage", choices=("all", "chain", "drafts"), default="all")
    add_model_arguments(parser)
    args = parser.parse_args()
    skills = sorted(args.skills.glob("*/SKILL.md"))
    if not skills:
        parser.error(f"No original skills in {args.skills}")
    for skill in skills:
        topic = (args.topics / (skill.parent.name + ".txt")).read_text(encoding="utf-8").strip()
        if not topic:
            parser.error(f"Empty topic for {skill.parent.name}")
        generate(skill, topic, args.out / skill.parent.name, args.backend, args.model, args.stage)


if __name__ == "__main__":
    main()
