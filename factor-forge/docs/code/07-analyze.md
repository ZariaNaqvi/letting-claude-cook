# 07 - `analyze.py`

## In one sentence

`analyze.py` turns `runs_scored.csv` into the project's results: pass rates with confidence intervals, statistical tests between models and conditions, per-task and cost tables, three figures, and a readable `summary.md`.

## Why it exists

`score.py` gives one row per run. That is 320 rows, too many to read. This file answers the actual research questions:

- Which model passes most often? (pass rate per model and condition)
- Is the difference between two models real or just luck? (Fisher exact tests)
- Does giving the recipe help? (RECIPE vs NAME_ONLY)
- Which factors are hard? (per-task pass rates, heatmap)
- How do models fail? (error-tag chart)
- What does a correct answer cost? (cost per correct answer)

## How to run it

From inside `~/letting-claude-cook/factor-forge` with the venv active:

```bash
python analyze.py              # results/runs_scored.csv -> results/ and figures/
python analyze.py --dry-run    # results_dryrun/ -> figures_dryrun/
```

You can also pass `--results FOLDER` and `--figures FOLDER`. Run `score.py` first.

Real output from the 128-run dry run (fake data, so the numbers mean nothing):

```
 model condition  passed  n  pass_rate           ci
 fable    RECIPE      12 16       75.0 [50.5, 89.8]
 fable NAME_ONLY      11 16       68.8 [44.4, 85.8]
  opus    RECIPE      11 16       68.8 [44.4, 85.8]
...
 haiku NAME_ONLY      10 16       62.5 [38.6, 81.5]

                 comparison a_pass b_pass  p_value  p_holm
      RECIPE: fable vs opus  12/16  11/16   1.0000  1.0000
     RECIPE: opus vs sonnet  11/16   9/16   0.7160  1.0000
...
 haiku: RECIPE vs NAME_ONLY  11/16  10/16   1.0000  1.0000

 model  runs  passed  total_cost_usd  cost_per_correct_usd
 fable    32      23          1.0780                0.0469
  opus    32      20          0.4295                0.0215
sonnet    32      22          0.2162                0.0098
 haiku    32      21          0.0110                0.0005

wrote .../results_dryrun/summary.md and 3 figures in .../figures_dryrun/
```

Files written to the results folder: `pass_rates.csv`, `fisher_tests.csv`, `task_pass_rates.csv`, `cost.csv`, `error_tags.csv`, `summary.md`. Figures: `pass_rate.png`, `task_heatmap.png`, `error_tags.png`.

In the full experiment, each model x condition cell has n = 8 tasks x 5 repeats = 40 runs.

## Walkthrough

### Imports and setup

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
```

**matplotlib** draws charts. `matplotlib.use("Agg")` picks a back end that writes image files without opening a window, so it works anywhere. It must come before importing `pyplot`. The `# noqa: E402` comments tell a style checker to ignore "import not at top of file".

```python
from scipy.stats import fisher_exact  # noqa: E402

from run_experiment import MODEL_ORDER, MODELS  # noqa: E402
```

`scipy` provides the Fisher exact test. Model names and order are imported from `run_experiment.py`, so they are defined in one place.

```python
LABEL = {a: MODELS[a][0].replace("claude-", "").replace("-", " ").title()
         .replace(" 5 5", " 5.5").replace(" 5 1", " 5.1") for a in MODELS}
```

Makes pretty labels for charts: `claude-opus-5-5` becomes `Opus 5.5`, `claude-fable-5-1` becomes `Fable 5.1`.

```python
COND_COLOR = {"RECIPE": "#2a78d6", "NAME_ONLY": "#eb6834"}
...
TAG_COLOR = dict(zip(TAG_ORDER, ["#2a78d6", "#eb6834", ...]))
```

Fixed colors: blue for RECIPE, orange for NAME_ONLY, and one fixed color per error tag. Fixed means a tag keeps its color in every chart. `zip` pairs up two lists item by item.

### `wilson(k, n, z=1.96)` - confidence interval for a pass rate

```python
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))
```

If a model passes 30 of 40 runs, its pass rate is 75%. But with only 40 runs, the true rate could plausibly be somewhat higher or lower. A **95% confidence interval** gives that plausible range.

The simple textbook interval (p plus or minus 1.96 x sqrt(p(1-p)/n)) breaks down for small samples and at the edges. At 0/40 or 40/40 it gives a width of zero, which claims perfect certainty. The **Wilson score interval** fixes that. It pulls the center slightly toward 50% and widens the range near 0% and 100%. Example: 0/40 gives roughly [0%, 8.8%], not [0%, 0%]. `z = 1.96` is the number of standard deviations for 95% confidence. The `max`/`min` keep the result between 0 and 1.

### `style(ax)`

Removes the top and right chart borders, greys the remaining ones, and adds light horizontal grid lines behind the bars. `ax` is a matplotlib "axes", one plot area.

### `main()` - loading

```python
    df = pd.read_csv(os.path.join(res_dir, "runs_scored.csv"))
    n_api = int((df["primary_tag"] == "API_ERROR").sum())
    df = df[df["primary_tag"] != "API_ERROR"].copy()     # infrastructure failures are not model failures
```

API errors are removed and counted. A network failure is not the model's fault, so it should not count against its pass rate. `df[condition]` is **boolean filtering**: keep only rows where the condition is True.

```python
    models = [m for m in MODEL_ORDER if m in set(df["model_alias"])]
    conds = [c for c in CONDITIONS if c in set(df["condition"])]
```

Keeps only models and conditions that actually appear, in the standard order. That lets the script work on a small pilot too.

### 1. Pass rate per model x condition

```python
            g = df[(df.model_alias == m) & (df.condition == c)]
            k, n = int(g.passed.sum()), len(g)
            lo, hi = wilson(k, n)
```

For each model and condition: `k` = passes (summing True/False counts the Trues), `n` = runs, and the Wilson interval. Saved to `pass_rates.csv`.

### 2. Fisher exact tests

```python
    def fisher(label, g1, g2):
        k1, n1, k2, n2 = int(g1.passed.sum()), len(g1), int(g2.passed.sum()), len(g2)
        if n1 and n2:
            _, p = fisher_exact([[k1, n1 - k1], [k2, n2 - k2]])
```

The question: are two pass rates really different, or could the gap be chance? The **Fisher exact test** works on a 2 x 2 table:

| | pass | fail |
|---|---|---|
| group A | k1 | n1 - k1 |
| group B | k2 | n2 - k2 |

It computes the exact probability of seeing a split at least this lopsided if both groups truly had the same pass rate. That probability is the **p-value**. A small p-value (say below 0.05) suggests a real difference. "Exact" means it does not rely on a large-sample approximation, which matters with 40 runs per group. The test is two-sided (it checks a difference in either direction). `fisher_exact` returns two numbers; the first (an odds ratio) is ignored with `_`.

```python
    for c in conds:
        for m1, m2 in zip(models, models[1:]):     # adjacent models in expected order
```

Which comparisons: within each condition, each model against the next one in the expected order (Fable vs Opus, Opus vs Sonnet, Sonnet vs Haiku). `zip(models, models[1:])` pairs each item with the next. Then, for each model, RECIPE vs NAME_ONLY. That is 6 + 4 = 10 tests.

```python
        order = ft["p_value"].sort_values().index
        m_tests, running = len(ft), 0.0
        for i, idx in enumerate(order):
            running = max(running, min(1.0, (m_tests - i) * ft.loc[idx, "p_value"]))
            ft.loc[idx, "p_holm"] = running
```

**Holm correction.** If you run 10 tests, one may look "significant" by luck. Holm's method adjusts for this. Sort p-values from smallest to largest. Multiply the smallest by 10, the next by 9, and so on. Cap at 1. `running = max(...)` makes sure the adjusted values never go down as you move along the sorted list. The result, `p_holm`, is what you compare with 0.05. Saved to `fisher_tests.csv`.

### 3. Per-task pass rates

```python
    tp = (df.groupby(["task", "model_alias", "condition"])["passed"]
          .agg(["sum", "count", "mean"]).reset_index()
          .rename(columns={"sum": "passed", "count": "n", "mean": "pass_rate"}))
```

**groupby** splits the table into groups (here one per task x model x condition), applies a calculation to each group, and combines the results. `.agg(["sum", "count", "mean"])` computes three things per group: passes, runs and pass rate. `.reset_index()` turns the group labels back into ordinary columns. Saved to `task_pass_rates.csv`.

### 4. Cost and latency

```python
            total = float(g.cost_usd.sum())
            cost_rows.append(dict(model=m, condition=c, runs=len(g), passed=k,
                                  mean_input_tokens=g.input_tokens.mean(), mean_output_tokens=g.output_tokens.mean(),
                                  total_cost_usd=total, cost_per_correct_usd=total / k if k else np.nan,
```

For each model, per condition and overall (`ALL`): average tokens, total dollars, mean and median latency, and **cost per correct answer** = total cost / number of passes. That is the practical number: a cheap model that rarely passes can cost more per correct answer than an expensive one that usually does. If a model never passes, it is NaN (undefined). Saved to `cost.csv`.

### 5. Error tags

```python
    fails = df[~df.passed]
    tags = pd.crosstab([fails.model_alias, fails.condition], fails.primary_tag)
```

Among failed runs only, count each primary tag per model and condition. `crosstab` builds the count table. Saved to `error_tags.csv`.

### Figure 1: headline bar chart (`pass_rate.png`)

```python
    for i, c in enumerate(conds):
        sub = pr[pr.condition == c].set_index("model").reindex(models)
        pos = x + (i - (len(conds) - 1) / 2) * (width + 0.03)
        ax.bar(pos, sub.pass_rate * 100, width, color=COND_COLOR[c], label=c.replace("_", " ").title(),
```

One group of bars per model, with two bars side by side (RECIPE and NAME_ONLY). `pos` shifts each condition's bars left or right of the model's position.

```python
        ax.errorbar(pos, sub.pass_rate * 100,
                    yerr=[(sub.pass_rate - sub.ci_low) * 100, (sub.ci_high - sub.pass_rate) * 100],
                    fmt="none", ecolor=INK, elinewidth=1, capsize=3)
```

Error bars show the Wilson interval. The interval is not symmetric, so `yerr` gives separate lower and upper lengths. Each bar also gets a small `passed/n` label at its base. The title states the pass rule.

### Figure 2: task heatmap (`task_heatmap.png`)

```python
    mat = np.full((len(tasks), len(cols)), np.nan)
    ...
    im = ax.imshow(mat, cmap="Blues", vmin=0, vmax=100, aspect="auto")
```

A grid: one row per factor, one column per model x condition. `np.full` makes a grid of NaN, then each cell is filled with the pass rate. `imshow` colors the grid (darker blue = higher pass rate) and each cell is labeled `passed/runs`. Text is white on dark cells and black on light ones. A color bar shows the scale. This shows which factors are hard for which models.

### Figure 3: error tags (`error_tags.png`)

```python
    for t in present:
        vals = np.array([tags.loc[(m, c), t] if (m, c) in tags.index else 0 for m, c in cols], dtype=float)
        ax.bar(range(len(cols)), vals, 0.7, bottom=bottom, label=t, color=TAG_COLOR.get(t, "#999999"),
               edgecolor="white", linewidth=1.5)
        bottom += vals
```

A **stacked** bar chart: one bar per model x condition, made of colored segments, one per error tag. `bottom` keeps track of where the next segment starts. Tags follow the fixed order and colors. Any tag not in the list gets grey.

### `summary.md`

```python
        "# Factor Forge results" + (" (DRY RUN - fake model, not real results)" if a.dry_run else ""),
```

Writes a Markdown report with all the tables: pass rates with CIs, Fisher tests, cost, error tags, and per-task pass rates (built with `pivot_table`, which reshapes long data into a grid: tasks as rows, model/condition as columns). Dry-run reports are clearly labeled as fake.

It ends with a caveat, which is worth repeating in any write-up: runs of the same task are not independent (a hard task is hard for every repeat), so the Fisher tests, which treat each run as independent, overstate precision. Report per-task results alongside.

Finally it prints the pass-rate table, the Fisher table and the overall cost table.

### `_table(d)` - DataFrame to Markdown

```python
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
```

Turns a DataFrame into a Markdown table by hand, so you do not need the extra `tabulate` package. Floats are formatted compactly: blank for NaN, scientific-style for tiny numbers (useful for small p-values), and up to 3 decimals with trailing zeros removed otherwise.

## If something goes wrong

- **`FileNotFoundError: .../results/runs_scored.csv`** - run `python score.py` first (or use `--dry-run` on both).
- **`ModuleNotFoundError: No module named 'scipy'`** (or `matplotlib`) - the venv is not active or requirements are not installed. Run `source .venv/bin/activate && pip install -r requirements.txt`.
- **Empty tables or a crash while drawing the figures** - check whether every run was an API_ERROR, so nothing is left after filtering. Check the `!` lines from `run_experiment.py`, fix the API problem, rerun it, then rescore.
- **Fisher table says "(not enough groups)"** - you only ran one model and one condition (for example, a tiny pilot). That is expected.

## Check your understanding

1. Why use a Wilson interval instead of the simple p plus or minus 1.96 x standard error?
2. What does a Fisher exact test p-value of 0.72 mean for "Opus vs Sonnet"?
3. Why are API errors removed before computing pass rates?

<details>
<summary>Answers</summary>

1. With small samples and rates near 0% or 100%, the simple interval is wrong. It can go below 0 or above 100, and at 0/40 or 40/40 it has zero width. Wilson stays inside 0-100% and gives a sensible range at the edges.
2. If both models truly had the same pass rate, a gap at least this big would happen about 72% of the time by chance. So there is no evidence of a real difference.
3. An API error is an infrastructure failure (network, rate limit), not a sign that the model could not do the task. Counting it would unfairly lower that model's pass rate.

</details>
