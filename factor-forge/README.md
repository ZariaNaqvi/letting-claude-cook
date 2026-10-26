# Factor Forge

**Can frontier LLMs exactly rebuild the official Fama-French factors from Ken French's raw CSV files?**

Course project for *Letting Claude Cook* (Harvard, Doug Finkbeiner) by Zaria Naqvi.
It follows up on my earlier *Replication Swarm* project. In that project Haiku, Sonnet and Opus all tied at rho = 0.945, because they were given pre-split files and only had to subtract two columns.

Here each model gets Ken French's raw portfolio CSVs as downloaded. Each file holds several stacked tables (value-weighted, equal-weighted, annual, firm counts and so on), and the model sees only the first 60 lines of each. It has to write one Python script that rebuilds a factor. The script's output is scored automatically against the official series French publishes.

| | |
|---|---|
| Factors (8) | HML, SMB (3-factor), SMB (5-factor), RMW, CMA, Mom, ST_Rev, LT_Rev (monthly) |
| Conditions | **RECIPE** (prompt gives the formula and the table) and **NAME_ONLY** ("construct HML exactly as Ken French does") |
| Models | claude-fable-5-1, claude-opus-5-5, claude-sonnet-5-5, claude-haiku-5-5, all at the same effort (`high`) |
| Repeats | 5 per cell, giving 8 x 2 x 4 x 5 = **320 runs** |
| PASS | the script runs, covers at least 95% of official months, and has **RMSE <= 1 bp** against the official series |
| Human reference | my rebuild (`ground_truth.py`) matches all 8 factors at RMSE 0.28-0.42 bp, which is rounding noise |

The scorer also tags each failed run with a cause: CRASH, NO_OUTPUT, BAD_FORMAT, WRONG_BLOCK (it used the equal-weighted table), SIGN_FLIP, UNITS (off by x100), DATE_MISALIGN, PARTIAL_COVERAGE or WRONG_FORMULA. Statistics are pass rates with Wilson 95% CIs and Fisher exact tests between adjacent models. The analysis also reports $ cost per correct answer.

## Reproduce in 5 commands

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env && chmod 600 .env          # then paste your ANTHROPIC_API_KEY into .env
python run_experiment.py --repeats 5            # 320 API calls, resumable (rerun the same command after Ctrl-C)
python score.py                                 # writes results/runs_scored.csv
python analyze.py                               # writes results/summary.md and figures/*.png
```

You can test everything for free, with no API key: `python selftest.py`, then `python run_experiment.py --dry-run --repeats 2 && python score.py --dry-run && python analyze.py --dry-run`. A dry run uses a fake model that plants known mistakes, and the scorer has to catch each one.

## Files

| file | purpose |
|---|---|
| `ground_truth.py` | my parser and factor recipes. Builds `data/truth` (official) and `data/reference` (rebuilt) |
| `tasks.json` | the 8 tasks: input files, RECIPE and NAME_ONLY text, the pass rule, and the files the model must never get |
| `prompts.py` | builds the prompt. The wording is identical for every model (frozen as `prompts-v1`) |
| `run_experiment.py` | calls the API, extracts the script, runs it in a clean temp folder (60 s limit) and logs tokens, $ and latency |
| `score.py` | compares each output to the official series, then assigns PASS/FAIL and an error tag |
| `analyze.py` | pass-rate table with CIs, Fisher tests, cost per correct answer, figures and `summary.md` |
| `dryrun_mock.py`, `selftest.py` | the fake model and the scorer self-test (88 planted mistakes, plus timeout and API-key-leak checks) |

## Results

*(to be filled in after the full run)*

![pass rate](figures/pass_rate.png)

## Notes on method

- **The models never see the answers.** The official factor files are never copied into the folder where a model's script runs.
- **Same conditions for every model.** Each run is a fresh API call: no system prompt, no tools, no web access. Temperature is left at the default, because these models reject sampling parameters. Effort is set to `high` for all four models, so the comparison is not confounded by different default efforts. No model fallbacks are used.
- **Prompts are frozen** (git tag `prompts-v1`) before the pilot. Any later change is logged in `notes.txt`. Each run stores the hash of its prompt.
- **Disclosure.** Claude Code helped build the harness, scorer and analysis code; that is the theme of the course. It never wrote or fixed the answers being evaluated. The human reference `ground_truth.py` was written with Claude's help and checked against French's official series.
- **Safety.** The scripts the models write run on my machine without an API key in their environment. This is not a full sandbox, so read a few scripts after the pilot.
- **Data.** Ken French Data Library, 202608 CRSP release, downloaded 2026-10-14.
