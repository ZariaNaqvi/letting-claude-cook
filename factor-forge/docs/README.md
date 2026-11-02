# Factor Forge docs: start here

**Factor Forge** tests whether Claude models can rebuild the official Fama-French factors from Ken French's raw data files. You grade every attempt automatically against the published answer. It is the course project for *Letting Claude Cook*, an upgrade of Replication Swarm.

The project has four parts:
- **Part 1 (Week 1, done):** download the raw files and build the answer key.
- **Part 2 (Week 2, done):** 320 runs where the models write a script from file previews. Result: 316/320 PASS, so the models tied.
- **Part 3, Form Forge (Oct 28 to Nov 3):** the harder test. The models get only a web browser and must click through SEC EDGAR to find book equity in filings made after their training cutoff.
- **Part 4 (Nov 4 to Nov 11):** analysis of Parts 2 and 3, the write-up and the talk.

## Read in this order

| # | Doc | Read it to learn | Time |
|---|---|---|---|
| 1 | [The project in plain English](01-the-project-in-plain-english.md) | What a factor is, what the models do, why this beats Replication Swarm | 10 min |
| 2 | [Goal, hypotheses and scoring](02-goal-hypotheses-and-scoring.md) | The research question, H1–H3 (Part 2), H1–H5 (Part 3), the run grids, how a pass is defined | 15 min |
| 3 | [Step-by-step checklist](03-step-by-step-checklist.md) | Every step, Oct 14 to Nov 11, with the exact commands and why | Use it as you work |
| 4 | [The data and its traps](04-the-data-and-its-traps.md) | The 11 files, the 8 recipes, the 11 file traps, and the SEC EDGAR traps of Part 3 | 15 min |
| 5 | [Glossary](05-glossary.md) | Finance, stats and software terms in one line each | Look things up |
| 6 | [Part 3 design: Form Forge](06-part3-form-forge-design.md) | Why SEC EDGAR, the tools, the access rules, the 8 tasks, cost, scoring, and what changed while building | 25 min |
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
| [08 config files](code/08-config-files.md) | `requirements.txt`, `.env.example`, `.gitignore` (and the Part 3 additions) | 1, 3 |
| [09 answer_key + tasks_web.json](code/09-answer_key-and-tasks_web.md) | `web/answer_key.py`: the Part 3 answer key | 3 |
| [10 sec_policy](code/10-sec_policy.md) | `web/sec_policy.py`: what the browser may load, and how fast | 3 |
| [11 browser_tools](code/11-browser_tools.md) | `web/browser_tools.py`: the browser and the 9 tools | 3 |
| [12 prompts_web](code/12-prompts_web.md) | `web/prompts_web.py`: the exact words every model sees | 3 |
| [13 run_web](code/13-run_web.md) | `web/run_web.py`: the agent loop | 3 |
| [14 mock_agent, capture_fixtures, selftest_web](code/14-mock_agent-capture_fixtures-selftest_web.md) | free tests of the Part 3 pipeline | 3 |
| [15 score_web + analyze_web](code/15-score_web-and-analyze_web.md) | Part 3 pass/fail, error tags, stats and figures | 3 |

## Other places things live

- **Full guide** (longer, with every file printed in full): https://claude.ai/artifact/HToxdCErddTAecizX4zbfk
- **Tested copy of all the code:** `~/factor-forge-build/`. It sits outside the repo. Copy files from it as the checklist says. (The Part 3 code was built straight into `factor-forge/web/`.)
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
Result     316/320 PASS, $11.16. The models tied.

PART 3: FORM FORGE (harder)
Question   Do they still tie when they must click through SEC EDGAR to find the inputs?
Tasks      book equity of 7 firms (T1–T7) + a 4-firm B/M ranking (T8), filed Jul–Aug 2026
Tools      a headless browser only (goto, read_page, find_text, click, fill, ...), no Python
Conditions STEPS (click path given) vs GOAL_ONLY (goal only)
Repeats    3        →  8 × 2 × 4 × 3 = 192 runs
Pass       exact whole-dollar value + the original filing's accession number
Budget     about $110 for 3 repeats (so likely 2 repeats, about $72), hard stop at $100 (--budget-usd 100)
Due        write-up + 10-minute talk on Nov 11
```
