# Experiment setup

[English](EXPERIMENTS.md) · [简体中文](EXPERIMENTS.zh-CN.md) · [README](README.md#evaluation)

## Data

The repository includes 582 values from the paper's main performance, distance, retention, and restoration curves and SkillDiff results in [data/curves.csv](data/curves.csv). Each row identifies the experiment, benchmark, model, condition, horizontal coordinate, and plotted value. Performance and retention use percentages, SkillDiff uses percentage points, and distance uses the normalized TF-IDF measure.

Original skill files and per-run model outputs are not bundled. The arXiv paper and Hugging Face dataset are coming soon.

For new model runs, prepare one selected original skill and one topic per task or skill ID.

```text
data/
  originals/
    <id>/
      SKILL.md
      ... companion scripts and reference files
  topics/
    <id>.txt
```

Each topic file contains the skill's one-sentence subject. The generation command uses the original skill's word count as the length target for both rewriting and topic-only drafts. For SkillsBench, use the task ID as `<id>` and copy the selected skill's companion files alongside `SKILL.md`.

## Models

| Subject model | Generation backend | Model argument | SkillsBench agent |
| --- | --- | --- | --- |
| GPT-5.6-Luna | codex | gpt-5.6-luna | codex-acp |
| GPT-6.1-Sol | codex | gpt-6.1-sol | codex-acp |
| MiMo-V2.5-Pro | api | mimo-v2.5-pro | openhands |
| Qwen3.7-Plus | api | qwen3.7-plus | openhands |
| Claude Haiku 5.5 | claude | claude-haiku-5-5 | claude-agent-acp |
| Qwen3.8-Flash | api | qwen3.8-flash | openhands |

Sign in to the CLI used by the selected backend. For the API backend, set `OPENAI_BASE_URL` and `OPENAI_API_KEY` for the provider. Codex generation uses high reasoning effort. Claude Code generation uses an empty system prompt with tools disabled. The API backend sends one user message at the provider's default thinking setting. The paper uses GPT-5.6-Luna as the item judge and restoration locator.

## Task evaluation

SkillsBench provides the task containers and verifiers. Install BenchFlow, configure its agent credentials, and place the SkillsBench checkout at `skillsbench/`. The paper uses codex-acp 1.6.2 for GPT-5.6-Luna, codex-acp 2.1.1 for GPT-6.1-Sol, and claude-agent-acp 0.40.0 for Claude Haiku 5.5. [SkillsBench setup](https://github.com/benchflow-ai/skillsbench#quick-start) · [BenchFlow](https://github.com/benchflow-ai/benchflow)

The `experiments.benchmark` command runs the selected conditions for each task in Docker. It reads the task verifier's binary result and writes `scores.csv`. Add `--dry-run` to inspect the commands. Choose a separate output directory for each evaluation batch.

For LogicBench and MedCalc-Bench, use SR-Agents' direct engine with the selected gold skill in the question prompt. The paper evaluates 760 LogicBench questions with 19 skills and 1,100 MedCalc-Bench questions with 55 skills. It uses minimal reasoning for the GPT models, no thinking for MiMo and Qwen, and low effort for Claude Haiku. [SR-Agents](https://github.com/oneal2000/SR-Agents)

To analyze task scores from either harness, export a CSV with these columns.

| Column | Meaning |
| --- | --- |
| `benchmark` | SkillsBench, LogicBench, or MedCalc-Bench |
| `model` | Model name |
| `condition` | original, round-1, round-5, round-10, round-30, restored-outside, restored-other, restored-all, or skilldiff |
| `task` | Task or question ID |
| `score` | Verifier result, 0 or 1 |

Use one row per task and condition from a single evaluation batch. The analysis compares matching task sets and calculates the percentage of tasks passed. The README gives the `--scores` command for each performance experiment.

## Text outputs

Each generated skill has its own folder under the chosen run directory.

```text
runs/luna/<id>/
  original.md
  input.json
  chain/01.md ... 30.md
  drafts/01.md ... 10.md
  items.json
  labels/draft-01.json ... draft-10.json
  labels/round-{01,05,10,30}.json
  locations.json
  restored/base.md
  restored/outside.md
  restored/other.md
  restored/all.md
  skilldiff.md
```

Generation writes the original, chain, and drafts. Judging writes the item inventory and labels for the ten drafts and rounds 1, 5, 10, and 30. Restoration writes the location records, common base, and three restored versions. SkillDiff writes the marked original.

For SkillDiff alone, generate with `--stage drafts` and judge with `--drafts-only`. These steps produce the original, ten self-written skills, item inventory, and draft labels without requiring rewritten skills.

The distance command measures every skill at rounds 0, 1, 2, 3, 5, 7, 10, 15, 20, 25, and 30, then reports their median.

The retention command reports the kept and decidable item counts for the 0, 1–3, 4–6, 7–9, and 10 draft-coverage groups at rounds 1 and 30. For the repeated chains on LogicBench and MedCalc-Bench, `--repeat` adds chains that share the first chain's original items and draft labels.
