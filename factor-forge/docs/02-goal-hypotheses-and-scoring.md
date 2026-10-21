# 2. Goal, hypotheses and scoring

## The research question

> Can frontier language models exactly rebuild the official Fama-French factors from Ken French's raw files? How does accuracy change with model size, and with whether the model is given the recipe?

## The three hypotheses

| | Hypothesis | What would support it |
|---|---|---|
| **H1** | Bigger models pass more often: Fable 5.1 > Opus 5.5 > Sonnet 5.5 > Haiku 5.5 | Pass rates ordered that way, with gaps larger than the confidence intervals |
| **H2** | Giving the recipe closes the gap between models | The RECIPE-minus-NAME_ONLY difference is biggest for the smaller models |
| **H3** | NAME_ONLY exposes knowledge gaps | Without the recipe, small models make "knowledge" errors (sign flips on reversal, SMB swap). With it, the remaining errors are mostly parsing (crash, wrong table) |

A result that rejects a hypothesis is still a result. If Haiku matches Opus, that's interesting. It would mean the task is about careful parsing rather than finance knowledge.

## The experiment grid

| Thing | Values | Count |
|---|---|---|
| Factors (tasks) | HML, SMB_3F, SMB_5F, RMW, CMA, MOM, ST_REV, LT_REV | 8 |
| Conditions | RECIPE, NAME_ONLY | 2 |
| Models | Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 5.5 | 4 |
| Repeats | the same prompt sent 5 times | 5 |
| **Total runs** | 8 × 2 × 4 × 5 | **320** |

**Why repeats?** A model can give different answers to the same prompt. With 5 tries per cell you measure a *rate* ("passes 4 out of 5 times") instead of a single lucky or unlucky shot.

**Why the same prompt for every model?** It is a controlled experiment. The only thing that changes between compared runs is the model, or the condition.

## What gets measured for every run

| Measure | Meaning | Unit |
|---|---|---|
| `ran` | Did the script finish without crashing within 60 seconds? | yes/no |
| `coverage` | Share of official months the output contains | 0–1 |
| `rmse_bp` | Root-mean-square error vs. the official series: the typical size of the monthly miss | basis points |
| `max_abs_err` | The single worst month's miss | basis points |
| `corr` | Correlation with the official series | −1 to 1 |
| **`passed`** | ran AND coverage ≥ 95% AND RMSE ≤ 1 bp | yes/no |
| `primary_tag` | Error type if it failed (below) | label |
| tokens, cost, latency | How many tokens, how many dollars, how many seconds | — |

### Why 1 bp?

You set it from your own answer key, not by guessing. Your correct code misses the official series by at most 0.42 bp (rounding). Twice that is 0.84 bp, so 1 bp is safely above rounding noise. Every wrong method you tested is at least 60 bp off. Nothing sits near the line.

### The error tags (how the scorer explains a failure)

| Tag | What happened |
|---|---|
| `CRASH` | Script threw an error or timed out |
| `NO_OUTPUT` | Script ran but did not write `output.csv` |
| `BAD_FORMAT` | `output.csv` exists but has the wrong columns or dates |
| `SIGN_FLIP` | Correlation near −1: right formula, backwards |
| `UNITS` | Off by a factor of 100 (decimals vs. percent) |
| `WRONG_BLOCK` | Used the equal-weighted or another wrong table |
| `DATE_MISALIGN` | Numbers right but shifted by a month |
| `PARTIAL_COVERAGE` | Right numbers, but too many months missing |
| `WRONG_FORMULA` | None of the above, just a different calculation |

The exact detection rules are in [code/06-score.md](code/06-score.md).

## How the results are summarized (Week 3)

- **Pass rate with a 95% Wilson confidence interval** for each model × condition. Wilson intervals behave well with small counts like 32 of 40, where the textbook formula breaks down.
- **Fisher exact tests** between neighboring models (e.g. Opus vs. Sonnet). They test whether a difference in pass rate is bigger than chance, and they work with small samples.
- **Heatmap** of pass rate by factor and model, which shows *which* factors are hard.
- **Cost per correct answer** = total dollars / number of passes. A cheap model that fails often can still cost more per correct answer.
- **Error-tag breakdown**, the "how they fail" chart that supports H3.

## Rules that keep the experiment honest

1. **The models being tested see only the harness prompt.** You can use Claude Code to help build the harness, scorer and charts, but never to write or fix a test model's answer.
2. **Freeze before you run.** Commit and `git tag` the prompts and harness before the full run, and don't edit prompts afterward. If you must change something, re-run everything.
3. **Log everything.** Every run saves the raw response, the extracted script, stdout/stderr, output and a `meta.json`. Commit them so anyone can check your work.
4. **Never commit your API key.** It lives in `.env`, which `.gitignore` excludes.
5. **Keep a lab notebook** (`notes.txt`), like your Replication Swarm notes: what you ran, when, and anything surprising.

Next: [03 — Step-by-step checklist](03-step-by-step-checklist.md)
