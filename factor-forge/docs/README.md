# Factor Forge docs: start here

**Factor Forge** tests whether Claude models can rebuild the official Fama-French factors from Ken French's raw data files. You grade every attempt automatically against the published answer. It is the course project for *Letting Claude Cook*, an upgrade of Replication Swarm.

## Read in this order

| # | Doc | Read it to learn | Time |
|---|---|---|---|
| 1 | [The project in plain English](01-the-project-in-plain-english.md) | What a factor is, what the models do, why this beats Replication Swarm | 10 min |
| 2 | [Goal, hypotheses and scoring](02-goal-hypotheses-and-scoring.md) | The research question, H1–H3, the 320-run grid, how a pass is defined | 10 min |
| 3 | [Step-by-step checklist](03-step-by-step-checklist.md) | Every step, Oct 14 to Nov 11, with the exact commands and why | Use it as you work |
| 4 | [The data and its traps](04-the-data-and-its-traps.md) | The 11 files, the 8 recipes, the 11 traps that separate good models from weak ones | 10 min |
| 5 | [Glossary](05-glossary.md) | Finance, stats and software terms in one line each | Look things up |
| — | [Code explained](code/) | Each Python file, walked through top to bottom | Before you run each file |

### Code explainers (in the order you'll use them)

| Doc | File | Week |
|---|---|---|
| [00 How the pieces fit](code/00-how-the-pieces-fit.md) | the whole pipeline in one diagram | 1 |
| [01 ground_truth](code/01-ground_truth.md) | `ground_truth.py`: builds the answer key | 1 |
| [02 make_tasks + tasks.json](code/02-make_tasks-and-tasks-json.md) | the 8 task definitions | 1 |
| [03 prompts](code/03-prompts.md) | `prompts.py`: the exact words every model sees | 2 |
| [04 run_experiment](code/04-run_experiment.md) | `run_experiment.py`: the harness | 2 |
| [05 dryrun_mock + selftest](code/05-dryrun_mock-and-selftest.md) | free tests of the pipeline | 2 |
| [06 score](code/06-score.md) | `score.py`: pass/fail and error tags | 2 |
| [07 analyze](code/07-analyze.md) | `analyze.py`: stats and figures | 3 |
| [08 config files](code/08-config-files.md) | `requirements.txt`, `.env.example`, `.gitignore` | 1 |

## Other places things live

- **Full guide** (longer, with every file printed in full): https://claude.ai/artifact/HToxdCErddTAecizX4zbfk
- **Tested copy of all the code:** `~/factor-forge-build/`. It sits outside the repo. Copy files from it as the checklist says.
- **This project folder:** `~/letting-claude-cook/factor-forge/`, inside your GitHub fork.
- **Your earlier project:** `~/replication-swarm/`

## The project on one card

```
Question   Can LLMs rebuild the Fama-French factors from raw files, exactly?
Models     Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 5.5
Tasks      HML, SMB_3F, SMB_5F, RMW, CMA, MOM, ST_REV, LT_REV
Conditions RECIPE (formula given) vs NAME_ONLY (model must know it)
Repeats    5        →  8 × 2 × 4 × 5 = 320 runs
Pass       script runs + ≥95% of months + RMSE ≤ 1 bp vs. official series
Budget     about $21–70 in API costs (set aside $50–100)
Due        write-up + 10-minute talk around Nov 11
```
