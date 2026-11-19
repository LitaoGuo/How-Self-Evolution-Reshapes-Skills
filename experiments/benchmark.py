"""Run SkillsBench conditions with BenchFlow and export task-level verifier scores."""

import argparse
import csv
import json
import math
from pathlib import Path
import shlex
import shutil
import subprocess

CONDITIONS = (
    "original", "round-1", "round-5", "round-10", "round-30",
    "restored-outside", "restored-other", "restored-all", "skilldiff",
)


def skill_file(run, condition):
    if condition == "original":
        return run / "original.md"
    if condition.startswith("round-"):
        return run / "chain" / f"{int(condition.split('-')[1]):02d}.md"
    if condition.startswith("restored-"):
        return run / "restored" / (condition.removeprefix("restored-") + ".md")
    return run / "skilldiff.md"


def verifier_score(jobs):
    records = []
    for file in jobs.rglob("result.json"):
        result = json.loads(file.read_text())
        if "rewards" in result:
            records.append(result)
    if len(records) != 1:
        raise ValueError(f"Expected one task result in {jobs}, found {len(records)}.")
    result = records[0]
    score = result["rewards"].get("reward")
    if result.get("error") or result.get("verifier_error") or score is None:
        raise ValueError(f"Benchmark did not produce a completed verifier result in {jobs}.")
    score = float(score)
    if not math.isfinite(score) or score not in (0, 1):
        raise ValueError(f"Expected a binary verifier result in {jobs}.")
    return score


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks-dir", type=Path, required=True)
    parser.add_argument("--skills", type=Path, required=True, help="selected originals with companion files")
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--conditions", nargs="+", choices=CONDITIONS, required=True)
    parser.add_argument("--agent", default="codex-acp")
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if len(args.conditions) != len(set(args.conditions)):
        parser.error("Each condition must appear once.")
    originals = sorted(args.runs.glob("*/original.md"))
    if not originals:
        parser.error(f"No generated skills in {args.runs}")
    for original in originals:
        if not (args.tasks_dir / original.parent.name).is_dir():
            parser.error(f"Missing benchmark task {original.parent.name}")
        if (args.skills / original.parent.name / "SKILL.md").read_bytes() != original.read_bytes():
            parser.error(f"Original skill changed for {original.parent.name}")
        for condition in args.conditions:
            if not skill_file(original.parent, condition).is_file():
                parser.error(f"Missing {condition} for {original.parent.name}")
    if args.out.exists() and not args.dry_run:
        parser.error(f"Choose a new output directory. {args.out} already exists.")
    if not args.dry_run:
        args.out.mkdir(parents=True)
    rows = []
    for original in originals:
        task = original.parent.name
        for condition in args.conditions:
            stage = args.out / "skills" / task / condition
            jobs = args.out / "jobs" / task / condition
            command = [
                "bench", "eval", "run", "--tasks-dir", str(args.tasks_dir.resolve()),
                "--include", task, "--agent", args.agent, "--model", args.model,
                "--sandbox", "docker", "--skill-mode", "with-skill",
                "--skills-dir", str(stage.resolve()), "--jobs-dir", str(jobs.resolve()),
            ]
            print(shlex.join(command), flush=True)
            if args.dry_run:
                continue
            shutil.copytree(args.skills / task, stage / task)
            shutil.copyfile(skill_file(original.parent, condition), stage / task / "SKILL.md")
            subprocess.run(command, check=True)
            rows.append({
                "benchmark": "SkillsBench", "model": args.model, "condition": condition,
                "task": task, "score": verifier_score(jobs),
            })
            with (args.out / "scores.csv").open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)


if __name__ == "__main__":
    main()
