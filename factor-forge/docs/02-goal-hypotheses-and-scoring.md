# 2. Goal, hypotheses and scoring

# Part 2: rebuilding the factors from files

## The research question

> Can frontier language models exactly rebuild the official Fama-French factors from Ken French's raw files? How does accuracy change with model size, and with whether the model is given the recipe?

## The three hypotheses (Part 2)

| | Hypothesis | What would support it |
|---|---|---|
| **H1** | Bigger models pass more often: Fable 5.1 > Opus 5.5 > Sonnet 5.5 > Haiku 5.5 | Pass rates ordered that way, with gaps larger than the confidence intervals |
| **H2** | Giving the recipe closes the gap between models | The RECIPE-minus-NAME_ONLY difference is biggest for the smaller models |
| **H3** | NAME_ONLY exposes knowledge gaps | Without the recipe, small models make "knowledge" errors (sign flips on reversal, SMB swap). With it, the remaining errors are mostly parsing (crash, wrong table) |

A result that rejects a hypothesis is still a result. If Haiku matches Opus, that's interesting. It would mean the task is about careful parsing rather than finance knowledge.

**What happened (full run, 2026-10-26):** 316/320 PASS. Sonnet 80/80, Haiku 79/80, Opus 79/80, Fable 78/80. RECIPE 160/160, NAME_ONLY 156/160. H1 is rejected: the biggest model was not the best. The 4 failures were coding slips (an impossible text search, a missed column, a pandas 3 read-only array), not knowledge errors. The pass rates sit at the ceiling, so H2 and H3 can't be tested well on this data. That is the reason for Part 3 below.

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

## How the results are summarized (Part 4)

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

---

# Part 3: Form Forge

## The research question

> Part 2 handed the models clean files, and they tied. When they must **find** the same kind of input themselves, by clicking through a real government website (SEC EDGAR), do they still tie? Or do model size and explicit instructions start to matter?

## The five hypotheses

| | Hypothesis | Builds on Part 2 | Test |
|---|---|---|---|
| **H1** (ceiling breaks) | The overall pass rate drops well below Part 2's 98.8%. Prediction: under 80% | 316/320 was a ceiling, not a measurement | Pass rate with a Wilson 95% CI; Fisher test vs 316/320, overall and per model |
| **H2** (bigger = better, retested) | Pass rates order Fable ≥ Opus ≥ Sonnet ≥ Haiku, and Fable beats Haiku | Part 2's H1 was rejected (Sonnet was top) | Fisher: Fable vs Haiku, Opus vs Sonnet, and adjacent models |
| **H3** (instructions matter more) | STEPS beats GOAL_ONLY by more than Part 2's RECIPE − NAME_ONLY gap (160/160 vs 156/160) | In Part 2 all 4 failures came without the recipe | Fisher, pooled and per model |
| **H4** (failures change type) | Most failures are finance or navigation mistakes, not step limits or give-ups | Part 2's failures were coding slips | Share of failures tagged WRONG_LINE, WRONG_PERIOD, UNITS, SIGN, WRONG_ENTITY, WRONG_FILING or NAV_ERROR |
| **H5** (efficiency) | Bigger models need fewer steps per success but cost more per correct answer; Haiku stays cheapest per correct answer | Haiku was nearly free and nearly perfect in Part 2 | Median steps per success; total $ ÷ passes, per model |

## The experiment grid

| Thing | Values | Count |
|---|---|---|
| Tasks | T1 Apple, T2 Microsoft, T3 Walmart, T4 Netflix, T5 Domino's, T6 JPMorgan (common equity), T7 Berkshire Hathaway, T8 four-firm B/M ranking | 8 |
| Conditions | STEPS (click path + row/column names + units hint), GOAL_ONLY (goal + general rules) | 2 |
| Models | Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 5.5, effort `high` | 4 |
| Repeats | 3 (or 2 if the pilot says 192 runs would cost over $100) | 3 |
| **Total runs** | 8 × 2 × 4 × 3 | **192** |

Every model gets the same system prompt, the same 9 tools, the same limits (30 tool calls, 50 for T8; 12 minutes) and `max_tokens` 16,000 per turn.

## What a pass means

A run **passes** when all three hold:
1. it ended with `submit_answer`, without `give_up`,
2. the value is **exactly** the key, in whole US dollars (tolerance $0). For T8, all four book equities are exact **and** the ranking is exact,
3. the accession number is the original filing for that period (or its amendment). T8 skips this check.

**Why tolerance $0?** The balance-sheet pages print exact millions or thousands, so the right answer in dollars is an exact integer. The key is built from SEC's XBRL data, which the models can't reach. For Apple it was checked three ways (the R4.htm page, companyfacts and frames).

## What gets measured for every run

| Measure | Meaning |
|---|---|
| `passed`, `primary_tag`, `tag_detail` | PASS or the first matching error tag, and why |
| `value_ok`, `accn_ok`, `period_ok` | Was the number, the accession and the date each right on its own |
| `grounded` | Did the submitted number appear on a page the model actually saw |
| `steps`, `turns`, `wall_s` | Tool calls, API turns, seconds |
| tokens and `cost_usd` | Input, output, cache-write and cache-read tokens, and dollars |
| `blocked_attempts` | How often it tried a blocked URL (for example the XBRL API) |
| `visited_search_form` | Did it use the EDGAR search page, or jump to a URL it knew |

## The error tags (Part 3)

A failed run gets the **first** tag that matches, in this order:

| Tag | What happened |
|---|---|
| `HARNESS_ERROR` | Harness crash, site outage, or SEC answered 403. Excluded and rerun, never a model failure |
| `STEP_LIMIT` | Used all its tool calls without answering |
| `TIME_LIMIT` | Ran past 12 minutes |
| `REFUSAL` | The API stopped with a refusal |
| `GAVE_UP` | Said `give_up`, or stopped calling tools |
| `UNGROUNDED` | The number never appeared on any page it saw: a guess |
| `WRONG_ENTITY` | Another company's number or filing |
| `NAV_ERROR` | Never reached the target filing |
| `UNITS` | Off by 1,000 or 1,000,000 (millions or thousands not converted) |
| `SIGN` | Right size, wrong sign (Domino's deficit) |
| `WRONG_PERIOD` | The same company's equity at another date (the comparative column) |
| `WRONG_LINE` | A look-alike row for the same date: equity incl. NCI, total liabilities and equity, total assets, preferred not subtracted |
| `WRONG_FILING` | Right number, wrong accession (a later filing that repeats it) |
| `ARITH` | T6: total equity and preferred were both seen, but the result is wrong. T8: all four values exact, but the ranking is wrong |
| `OTHER_WRONG` | Anything else; read these by hand |

The exact rules are in [code/15-score_web-and-analyze_web.md](code/15-score_web-and-analyze_web.md).

## How the results are summarized

`web/analyze_web.py` writes, to `results_web/`:
- pass rates with Wilson 95% CIs (overall, by model, condition, task, model × condition),
- Fisher tests for H1–H3 with Holm-adjusted p-values,
- the error-tag table and the finance/navigation share (H4),
- steps per success and **cost per correct answer** (H5),
- how often each model tried a blocked URL or used the search form,
- three figures and `summary.md`, which starts with the **Part 2 vs Part 3** table.

## Extra rules for Part 3

1. **Never let the models reach the key.** The browser blocks `data.sec.gov/api/xbrl`.
2. **Respect SEC's rules.** A declared User-Agent (`SEC_USER_AGENT` in `.env`), at most 5 requests per second, robots.txt obeyed, one run at a time.
3. **Freeze before you run.** Set `PROMPT_VERSION = "web-v1"` after the hand walk, tag it, and don't change prompts after the main run starts.
4. **Pilot runs are never pooled** with the main run.
5. **Never commit `.env`,** and check that your User-Agent contact address is not in any run file (it is stored only as a sha256).

Next: [03 — Step-by-step checklist](03-step-by-step-checklist.md)
