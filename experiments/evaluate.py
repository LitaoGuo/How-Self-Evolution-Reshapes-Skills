"""Analyze and plot one experiment from published curves or task-level scores."""

import argparse
from collections import defaultdict
import csv
from pathlib import Path
from statistics import mean
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA = Path(__file__).resolve().parents[1] / "data" / "curves.csv"
EXPERIMENTS = ("performance", "distance", "retention", "restoration", "skilldiff")
BENCHMARKS = ("SkillsBench", "LogicBench", "MedCalc-Bench")
MODELS = ("GPT-5.6-Luna", "GPT-6.1-Sol", "MiMo-V2.5-Pro", "Qwen3.7-Plus", "Claude Haiku 5.5", "Qwen3.8-Flash")
LABELS = {
    "rewritten": "Rewritten skill", "round-1": "Round 1", "round-30": "Round 30",
    "restored-outside": "0/10 items restored", "restored-other": "≥1/10 items restored",
}
COLORS = {
    "rewritten": "#527aa8", "round-1": "#a7c4e1", "round-30": "#527aa8",
    "restored-outside": "#dd8958", "restored-other": "#a7c4e1",
}


def read_curves(path, experiment):
    with path.open(encoding="utf-8", newline="") as file:
        rows = [row for row in csv.DictReader(file) if row["experiment"] == experiment]
    curves = defaultdict(list)
    for row in rows:
        curves[row["benchmark"], row["model"], row["condition"]].append((float(row["x"]), float(row["value"])))
    if not curves:
        raise ValueError(f"No {experiment} values in {path}")
    for points in curves.values():
        points.sort()
    return dict(curves)


def read_scores(path, experiment):
    required = {
        "performance": ("original", "round-1", "round-5", "round-10", "round-30"),
        "restoration": ("original", "round-30", "restored-outside", "restored-other"),
        "skilldiff": ("original", "skilldiff"),
    }[experiment]
    groups = defaultdict(dict)
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            key = row["benchmark"], row["model"], row["condition"]
            score = float(row["score"])
            if not math.isfinite(score) or score not in (0, 1):
                raise ValueError("Each task score must be zero or one.")
            if row["task"] in groups[key]:
                raise ValueError(f"Repeated task {row['task']} in {key}")
            groups[key][row["task"]] = score
    if not groups:
        raise ValueError(f"No task scores in {path}")
    if experiment == "skilldiff" and {key[0] for key in groups} != {"SkillsBench"}:
        raise ValueError("The SkillDiff evaluation uses SkillsBench.")
    panels = sorted({key[:2] for key in groups})
    curves = {}
    for benchmark, model in panels:
        prefix = benchmark, model
        tasks = set(groups[prefix + ("original",)])
        if not tasks or any(set(groups[prefix + (condition,)]) != tasks for condition in required):
            raise ValueError(f"{benchmark}/{model} requires the same tasks in every condition.")
        scores = {condition: 100 * mean(groups[prefix + (condition,)].values()) for condition in required}
        if experiment == "performance":
            curves[prefix + ("rewritten",)] = list(zip((0, 1, 5, 10, 30), scores.values()))
        elif experiment == "restoration":
            curves[prefix + ("rewritten",)] = [(0, scores["original"]), (1, scores["round-30"])]
            for condition in ("restored-outside", "restored-other"):
                curves[prefix + (condition,)] = [(1, scores["round-30"]), (2, scores[condition])]
        else:
            curves[prefix + ("skilldiff",)] = [(0, scores["skilldiff"] - scores["original"])]
    return curves


def report(curves, experiment):
    for benchmark in dict.fromkeys(key[0] for key in curves):
        selected = {key: points for key, points in curves.items() if key[0] == benchmark}
        if experiment == "performance":
            values = [points[-1][1] - points[0][1] for points in selected.values()]
            print(f"{benchmark} · Round-30 score change {mean(values):+.1f} pp")
        elif experiment == "distance":
            print(f"{benchmark} · Mean distance {mean(p[0][1] for p in selected.values()):.2f}"
                  f" → {mean(p[-1][1] for p in selected.values()):.2f}")
        elif experiment == "retention":
            points = [p for key, p in selected.items() if key[2] == "round-30"]
            print(f"{benchmark} · Round-30 retention, 0/10 {mean(p[0][1] for p in points):.1f}%"
                  f", 10/10 {mean(p[-1][1] for p in points):.1f}%")
        elif experiment == "restoration":
            for condition in ("restored-outside", "restored-other"):
                gains = [p[-1][1] - p[0][1] for key, p in selected.items() if key[2] == condition]
                print(f"{benchmark} · {LABELS[condition]} {mean(gains):+.1f} pp")
        else:
            print(f"{benchmark} · SkillDiff gain {mean(p[0][1] for p in selected.values()):+.1f} pp")
    if experiment == "retention":
        points = [values for key, values in curves.items() if key[2] == "round-30"]
        print(f"Across models and benchmarks · 0/10 {mean(p[0][1] for p in points):.1f}%"
              f", 10/10 {mean(p[-1][1] for p in points):.1f}%")


def plot(curves, experiment, output):
    models = sorted({key[1] for key in curves}, key=lambda x: (x not in MODELS, MODELS.index(x) if x in MODELS else x))
    benchmarks = sorted({key[0] for key in curves}, key=lambda x: (x not in BENCHMARKS, BENCHMARKS.index(x) if x in BENCHMARKS else x))
    if experiment == "skilldiff":
        figure, axis = plt.subplots(figsize=(9, 4.5))
        values = [curves["SkillsBench", model, "skilldiff"][0][1] for model in models]
        bars = axis.bar(models, values, color="#527aa8")
        axis.bar_label(bars, labels=[f"+{value:.1f}" for value in values], padding=4)
        axis.set_ylabel("Pass-rate gain (percentage points)")
        axis.tick_params(axis="x", rotation=25)
        figure.tight_layout()
    else:
        figure, axes = plt.subplots(len(benchmarks), len(models), squeeze=False,
                                    figsize=(3.1 * len(models), 2.8 * len(benchmarks)))
        legend = {}
        for row, benchmark in enumerate(benchmarks):
            for col, model in enumerate(models):
                axis = axes[row, col]
                panel = {key[2]: values for key, values in curves.items() if key[:2] == (benchmark, model)}
                if not panel:
                    axis.set_visible(False)
                    continue
                for condition, points in panel.items():
                    x, y = zip(*points)
                    line, = axis.plot(x, y, marker="o", markersize=3, color=COLORS[condition], label=LABELS[condition])
                    legend[LABELS[condition]] = line
                if experiment in ("performance", "distance", "restoration"):
                    baseline = panel["rewritten"][0][1]
                    line = axis.axhline(baseline, color="#dd8958", linestyle="--", linewidth=1, label="Original skill")
                    legend["Original skill"] = line
                if experiment == "retention":
                    axis.set_xticks([0, 2, 5, 8, 10], ["0", "1–3", "4–6", "7–9", "10"])
                    axis.set_ylim(0, 102)
                if experiment == "restoration":
                    axis.set_xticks([0, 1, 2], ["Original", "Round 30", "Restored"], rotation=25)
                axis.grid(alpha=.2)
                if row == 0:
                    axis.set_title(model, fontsize=10)
                if col == 0:
                    metric = {"performance": "Score (%)", "distance": "Normalized TF-IDF distance",
                              "retention": "Retention (%)", "restoration": "Score (%)"}[experiment]
                    axis.set_ylabel(benchmark + "\n" + metric)
                if row == len(benchmarks) - 1:
                    label = "Self-written drafts stating the item" if experiment == "retention" else "Round"
                    if experiment != "restoration":
                        axis.set_xlabel(label)
        figure.legend(legend.values(), legend.keys(), loc="upper center", ncol=len(legend), frameon=False)
        figure.tight_layout(rect=(0, 0, 1, .94))
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", choices=EXPERIMENTS)
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--scores", type=Path, help="CSV of benchmark, model, condition, task, score")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.scores and args.experiment not in ("performance", "restoration", "skilldiff"):
        parser.error("--scores applies to task-performance experiments.")
    curves = read_scores(args.scores, args.experiment) if args.scores else read_curves(args.data, args.experiment)
    report(curves, args.experiment)
    output = args.out or Path("outputs") / (args.experiment + ".png")
    plot(curves, args.experiment, output)
    print(output)


if __name__ == "__main__":
    main()
