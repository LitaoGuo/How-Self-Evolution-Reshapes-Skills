# 实验准备

[English](EXPERIMENTS.md) · [简体中文](EXPERIMENTS.zh-CN.md) · [返回首页](README.zh-CN.md#实验评估)

## 数据

仓库在 [data/curves.csv](data/curves.csv) 中提供了论文主要任务表现、距离、保留率、恢复实验曲线及 SkillDiff 结果的 582 个数值。每行记录实验、基准、模型、条件、横坐标和数值。任务表现与保留率的单位为百分比，SkillDiff 为百分点，距离采用归一化 TF-IDF 度量。

仓库暂未包含原始技能文件和逐次模型运行输出。arXiv 论文与 Hugging Face 数据集入口均待发布。

运行新实验时，为每个任务或技能 ID 准备一份选定的原始技能及其主题。

```text
data/
  originals/
    <id>/
      SKILL.md
      ... 配套脚本和参考文件
  topics/
    <id>.txt
```

每个主题文件用一句话描述技能主题。生成命令以原始技能的词数作为改写稿和自写稿的目标长度。对于 SkillsBench，`<id>` 使用任务 ID，并将选定技能的配套文件与 `SKILL.md` 一起放入目录。

## 模型

| 实验模型 | 生成接口 | 模型参数 | SkillsBench 智能体 |
| --- | --- | --- | --- |
| GPT-5.6-Luna | codex | gpt-5.6-luna | codex-acp |
| GPT-6.1-Sol | codex | gpt-6.1-sol | codex-acp |
| MiMo-V2.5-Pro | api | mimo-v2.5-pro | openhands |
| Qwen3.7-Plus | api | qwen3.7-plus | openhands |
| Claude Haiku 5.5 | claude | claude-haiku-5-5 | claude-agent-acp |
| Qwen3.8-Flash | api | qwen3.8-flash | openhands |

登录所选接口对应的命令行工具。使用 API 接口时，设置提供商的 `OPENAI_BASE_URL` 和 `OPENAI_API_KEY`。Codex 生成使用 high 推理强度；Claude Code 生成关闭工具并使用空系统提示；API 接口发送一条用户消息，采用提供商默认的思考设置。论文使用 GPT-5.6-Luna 判读条目并定位恢复位置。

## 任务评测

SkillsBench 提供任务容器和验证器。安装 BenchFlow，配置智能体凭据，并将 SkillsBench 仓库放在 `skillsbench/`。论文中 GPT-5.6-Luna 使用 codex-acp 1.6.2，GPT-6.1-Sol 使用 codex-acp 2.1.1，Claude Haiku 5.5 使用 claude-agent-acp 0.40.0。[SkillsBench 安装说明](https://github.com/benchflow-ai/skillsbench#quick-start) · [BenchFlow](https://github.com/benchflow-ai/benchflow)

`experiments.benchmark` 在 Docker 中为每个任务运行选定条件，读取任务验证器的二元结果，写入 `scores.csv`。添加 `--dry-run` 可以查看将要执行的命令。每批评测使用独立的输出目录。

LogicBench 和 MedCalc-Bench 使用 SR-Agents 的 direct 引擎，将选定的 gold skill 放入问题提示。论文评测了 LogicBench 的 760 道题、19 份技能，以及 MedCalc-Bench 的 1,100 道题、55 份技能。GPT 模型使用 minimal 推理强度，MiMo 和 Qwen 关闭思考，Claude Haiku 使用 low 强度。[SR-Agents](https://github.com/oneal2000/SR-Agents)

分析任一评测框架的任务得分时，导出包含下列列名的 CSV。

| 列名 | 含义 |
| --- | --- |
| `benchmark` | SkillsBench、LogicBench 或 MedCalc-Bench |
| `model` | 模型名称 |
| `condition` | original、round-1、round-5、round-10、round-30、restored-outside、restored-other、restored-all 或 skilldiff |
| `task` | 任务或问题 ID |
| `score` | 验证器结果，0 或 1 |

同一批评测中，每个任务在每个条件下各占一行。分析命令比较相同的任务集合，并计算通过任务所占的百分比。首页在相应实验下给出了 `--scores` 命令。

## 文本输出

每份技能在指定运行目录下拥有独立文件夹。

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

生成步骤写入原技能、改写链和自写稿。判读步骤写入条目清单，以及 10 份自写稿和第 1、5、10、30 轮改写稿的标签。恢复步骤写入位置记录、共同底稿和三个恢复版本。SkillDiff 写入标记后的原技能。

单独运行 SkillDiff 时，生成步骤使用 `--stage drafts`，判读步骤使用 `--drafts-only`。这两步生成原技能、10 份自写技能、条目清单和自写稿标签，无需改写稿。

距离命令测量每份技能在第 0、1、2、3、5、7、10、15、20、25、30 轮的距离，并报告各轮中位数。

保留率命令按自写稿覆盖次数分为 0、1–3、4–6、7–9、10 五组，报告第 1 和 30 轮的保留条目数与可判定条目数。对 LogicBench 和 MedCalc-Bench 的重复改写链，可使用 `--repeat` 添加与首条链共享原始条目及自写稿标签的改写链。
