# 15 - `web/score_web.py` and `web/analyze_web.py`

## In one sentence

`score_web.py` gives each run PASS or an error tag against the frozen key, and `analyze_web.py` turns the scored runs into the H1–H5 tables, tests and figures.

## `score_web.py`

```bash
python web/score_web.py --runs runs_web --out results_web
```

Without `--out`, it replaces `runs_web` with `results_web` in the path. It reads every `final.json`, the run's `pages/*.txt` and `web/answer_key.json`, and writes `runs_scored.csv`.

**PASS** = answered without `give_up`, value exactly the key, and the accession in the key's allowed list (original filing or its amendment). T8: all four values exact and the ranking exact; accessions not checked.

### The error tags (the first that matches wins)

| tag | how it is detected |
|---|---|
| HARNESS_ERROR | Harness exception, 3 site errors, an SEC 403, or the budget ran out mid-run. Excluded from the analysis and rerun, never counted as a model failure |
| STEP_LIMIT | Hit the tool-call cap without an answer |
| TIME_LIMIT | Hit the 12-minute cap |
| REFUSAL | The API stopped with `stop_reason` `refusal` |
| GAVE_UP | `give_up: true`, or the model stopped calling tools without an answer (any stop other than `answered`) |
| UNGROUNDED | The number never appeared on any page the run saw, in any display form (107,520 / 107,520,000 / 107520000000 / (3,982,431)). A guess. T6 is also grounded if total equity and preferred both appear |
| WRONG_ENTITY | The accession belongs to another company, or the value is another company's in the frames snapshot |
| NAV_ERROR | The target filing's folder is in no visited URL and its accession is on no page: the model never got there |
| UNITS | value / key is 10³, 10⁶, 10⁻³ or 10⁻⁶ |
| SIGN | value = −key |
| WRONG_PERIOD | The same company's equity at another date (comparative column, prior quarter) |
| WRONG_LINE | A look-alike line for the same date: incl. NCI, total liabilities and equity, preferred not subtracted, liquidation preference, total assets |
| WRONG_FILING | Right value, wrong accession (a later filing that repeats the number) |
| ARITH | T6: total equity and preferred were both seen, but the result is wrong. T8: all four values exact, but the ranking is wrong |
| OTHER_WRONG | Anything else. Read every one of these by hand |

How the trickier ones are detected (`diagnose`):
- **Display forms:** `display_forms` writes the value in dollars, thousands, millions and billions, with and without commas, and only keeps forms of 4+ digits so short numbers don't match by accident. It uses the absolute value, so a negative printed as (3,982,431) still counts.
- **WRONG_PERIOD / WRONG_LINE / WRONG_FILING:** the value equals a look-alike recorded by `answer_key.py`.
- **T8:** the worst per-firm tag in the order above; if all four values are right but the order is wrong, ARITH.

**Why UNGROUNDED comes before NAV_ERROR.** A model that guesses never reaches the filing either. Checking grounding first means a guess is called a guess, not a navigation error. The same goes for WRONG_ENTITY: a model on the wrong company never reaches the right filing.

**One edge case: WRONG_FILING vs NAV_ERROR.** Only T4 (NFLX) has a later filing that repeats the number (`0001065280-26-000291`). WRONG_FILING is checked after NAV_ERROR, so a model that jumps straight to the later filing and never sees the original accession (`0001065280-26-000212`) on any page is tagged NAV_ERROR. If it came through the filing list, the original accession is on that page and it gets WRONG_FILING. Either way it fails; only the tag differs. Hand-check any T4 NAV_ERROR.

Columns include `passed`, `primary_tag`, `tag_detail`, `value_ok`, `accn_ok`, `period_ok`, `grounded`, `submitted_value`, `submitted_accession`, `steps`, tokens, `cost_usd`, `wall_s`, `blocked_attempts`, `visited_search_form`, `network_requests`, `prompt_sha`, `prompt_version`.

**Dry run check:** if the runs came from personas, it compares each tag with `mock_agent.EXPECTED_TAG` (and `api` must have `blocked_attempts` > 0), writes `dryrun_check.csv` and prints `N mismatches`. Real output (Oct 28, 18 live dry runs):

```
scored 18 runs ... PASS 4, WRONG_PERIOD 2, GAVE_UP 2, UNGROUNDED 2, STEP_LIMIT 2, UNITS 2, WRONG_ENTITY 2, WRONG_LINE 2
0 mismatches
```

## `analyze_web.py`

```bash
python web/analyze_web.py --in results_web/runs_scored.csv --part2 results/runs_scored.csv --out results_web
```

HARNESS_ERROR runs are dropped first. It reuses Part 2's `wilson` and plotting style from `analyze.py`.

| output | contents |
|---|---|
| `pass_rates.csv` | Wilson 95% CIs: overall, by model, condition, task, model × condition |
| `fisher_tests.csv` | H1 Part 2 vs Part 3 (all and per model; Part 2 `API_ERROR` rows dropped), H2 Fable vs Haiku, Opus vs Sonnet and adjacent models, H3 STEPS vs GOAL_ONLY pooled and per model; Holm-adjusted `p_holm` |
| `error_tags.csv` | model × tag and condition × tag, failed runs only |
| `efficiency.csv` | runs, passes, median and IQR of steps per success, tokens, total $, $ per correct answer |
| `behavior.csv` | share of runs with a blocked attempt, share that used the search form |
| `summary.md` | all of the above, starting with the Part 2 vs Part 3 table; headed DRY RUN if the runs are fake |
| figures | `fig_task_heatmap.png`, `fig_cost_per_correct.png`, `fig_steps_success.png` |

It also prints the share of failures in the finance/navigation tags (WRONG_LINE, WRONG_PERIOD, UNITS, SIGN, WRONG_ENTITY, WRONG_FILING, NAV_ERROR) for H4. Real output on the dry run (fake numbers, only to show the format):

```
overall all 4 18 22.2 [9.0, 45.2]
H1 all models: Part 2 vs Part 3 316/320 4/18 0.0000 0.0000
share of failures in finance/navigation tags: 57%
wrote results_web_mock/summary.md, 5 CSVs and 3 figures
```

## Things to check

- Hand-check 20 runs. If a tag is wrong, fix the scorer and **rescore**; never rerun the models.
