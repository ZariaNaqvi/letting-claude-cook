"""
Factor Forge -- analysis: tables, statistics and figures.

Input : results/runs_scored.csv            (from score.py)
Output: results/pass_rates.csv             pass rate per model x condition, Wilson 95% CI
        results/fisher_tests.csv           Fisher exact tests (adjacent models; RECIPE vs NAME_ONLY)
        results/task_pass_rates.csv        pass rate per task x model x condition
        results/cost.csv                   tokens, $ and cost per correct answer per model
        results/error_tags.csv             primary error tag counts
        results/summary.md                 all of the above as one readable report
        figures/pass_rate.png              HEADLINE: grouped bars, pass rate by model and condition
        figures/task_heatmap.png           pass rate per task (rows) x model/condition (columns)
        figures/error_tags.png             what went wrong, by model and condition

    python analyze.py              # real results
    python analyze.py --dry-run    # results_dryrun/ -> figures_dryrun/
"""
import argparse
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import fisher_exact  # noqa: E402

from run_experiment import MODEL_ORDER, MODELS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CONDITIONS = ["RECIPE", "NAME_ONLY"]
LABEL = {a: MODELS[a][0].replace("claude-", "").replace("-", " ").title()
         .replace(" 5 5", " 5.5").replace(" 5 1", " 5.1") for a in MODELS}

# Colors (validated categorical slots 1-2 of the dataviz reference palette)
COND_COLOR = {"RECIPE": "#2a78d6", "NAME_ONLY": "#eb6834"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
# Error tags in a fixed order with fixed colors (color follows the tag, never its rank)
TAG_ORDER = ["WRONG_FORMULA", "WRONG_BLOCK", "SIGN_FLIP", "UNITS", "DATE_MISALIGN",
             "PARTIAL_COVERAGE", "BAD_FORMAT", "NO_OUTPUT", "CRASH", "TIMEOUT",
             "NO_CODE", "MAX_TOKENS", "REFUSAL"]
TAG_COLOR = dict(zip(TAG_ORDER, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300",
                                 "#6250d6", "#e34948", "#8a8984", "#b5b4ae", "#3b3a37", "#d2d1cb",
                                 "#6f6e69"]))


def wilson(k, n, z=1.96):
    """Wilson score 95% interval for k successes out of n (good for small n and 0%/100%)."""
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelcolor=INK)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def main():
    ap = argparse.ArgumentParser(description="Make tables and figures from runs_scored.csv")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--results", default=None)
    ap.add_argument("--figures", default=None)
    a = ap.parse_args()
    res_dir = a.results or os.path.join(HERE, "results_dryrun" if a.dry_run else "results")
    fig_dir = a.figures or os.path.join(HERE, "figures_dryrun" if a.dry_run else "figures")
    os.makedirs(fig_dir, exist_ok=True)

    df = pd.read_csv(os.path.join(res_dir, "runs_scored.csv"))
    n_api = int((df["primary_tag"] == "API_ERROR").sum())
    df = df[df["primary_tag"] != "API_ERROR"].copy()     # infrastructure failures are not model failures
    df["passed"] = df["passed"].astype(bool)
    models = [m for m in MODEL_ORDER if m in set(df["model_alias"])]
    conds = [c for c in CONDITIONS if c in set(df["condition"])]
    import json
    task_order = [t["id"] for t in json.load(open(os.path.join(HERE, "tasks.json")))["tasks"]]
    tasks = [t for t in task_order if t in set(df["task"])]   # same order as tasks.json

    # ---------------- 1. pass rate per model x condition ----------------
    rows = []
    for m in models:
        for c in conds:
            g = df[(df.model_alias == m) & (df.condition == c)]
            k, n = int(g.passed.sum()), len(g)
            lo, hi = wilson(k, n)
            rows.append(dict(model=m, model_id=MODELS[m][0], condition=c, passed=k, n=n,
                             pass_rate=k / n if n else np.nan, ci_low=lo, ci_high=hi))
    pr = pd.DataFrame(rows)
    pr.to_csv(os.path.join(res_dir, "pass_rates.csv"), index=False)

    # ---------------- 2. Fisher exact tests ----------------
    tests = []

    def fisher(label, g1, g2):
        k1, n1, k2, n2 = int(g1.passed.sum()), len(g1), int(g2.passed.sum()), len(g2)
        if n1 and n2:
            _, p = fisher_exact([[k1, n1 - k1], [k2, n2 - k2]])
            tests.append(dict(comparison=label, a_pass=f"{k1}/{n1}", b_pass=f"{k2}/{n2}", p_value=p))

    for c in conds:
        for m1, m2 in zip(models, models[1:]):     # adjacent models in expected order
            fisher(f"{c}: {m1} vs {m2}", df[(df.model_alias == m1) & (df.condition == c)],
                   df[(df.model_alias == m2) & (df.condition == c)])
    if len(conds) == 2:
        for m in models:
            fisher(f"{m}: RECIPE vs NAME_ONLY", df[(df.model_alias == m) & (df.condition == "RECIPE")],
                   df[(df.model_alias == m) & (df.condition == "NAME_ONLY")])
    ft = pd.DataFrame(tests)
    if len(ft):
        # Holm correction across all tests in this table (simple, conservative)
        order = ft["p_value"].sort_values().index
        m_tests, running = len(ft), 0.0
        for i, idx in enumerate(order):
            running = max(running, min(1.0, (m_tests - i) * ft.loc[idx, "p_value"]))
            ft.loc[idx, "p_holm"] = running
    ft.to_csv(os.path.join(res_dir, "fisher_tests.csv"), index=False)

    # ---------------- 3. per-task pass rates ----------------
    tp = (df.groupby(["task", "model_alias", "condition"])["passed"]
          .agg(["sum", "count", "mean"]).reset_index()
          .rename(columns={"sum": "passed", "count": "n", "mean": "pass_rate"}))
    tp.to_csv(os.path.join(res_dir, "task_pass_rates.csv"), index=False)

    # ---------------- 4. cost and latency ----------------
    cost_rows = []
    for m in models:
        for c in conds + ["ALL"]:
            g = df[df.model_alias == m] if c == "ALL" else df[(df.model_alias == m) & (df.condition == c)]
            k = int(g.passed.sum())
            total = float(g.cost_usd.sum())
            cost_rows.append(dict(model=m, condition=c, runs=len(g), passed=k,
                                  mean_input_tokens=g.input_tokens.mean(), mean_output_tokens=g.output_tokens.mean(),
                                  total_cost_usd=total, cost_per_correct_usd=total / k if k else np.nan,
                                  mean_latency_s=g.latency_s.mean(), median_latency_s=g.latency_s.median()))
    cost = pd.DataFrame(cost_rows)
    cost.to_csv(os.path.join(res_dir, "cost.csv"), index=False)

    # ---------------- 5. error tags ----------------
    fails = df[~df.passed]
    tags = pd.crosstab([fails.model_alias, fails.condition], fails.primary_tag)
    tags.to_csv(os.path.join(res_dir, "error_tags.csv"))

    # ---------------- Figure 1: headline grouped bar chart ----------------
    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=150)
    x = np.arange(len(models))
    width = 0.36
    for i, c in enumerate(conds):
        sub = pr[pr.condition == c].set_index("model").reindex(models)
        pos = x + (i - (len(conds) - 1) / 2) * (width + 0.03)
        ax.bar(pos, sub.pass_rate * 100, width, color=COND_COLOR[c], label=c.replace("_", " ").title(),
               edgecolor="white", linewidth=1.5)
        ax.errorbar(pos, sub.pass_rate * 100,
                    yerr=[(sub.pass_rate - sub.ci_low) * 100, (sub.ci_high - sub.pass_rate) * 100],
                    fmt="none", ecolor=INK, elinewidth=1, capsize=3)
        for px, r in zip(pos, sub.itertuples()):
            ax.text(px, 2, f"{r.passed}/{r.n}", ha="center", va="bottom", fontsize=7.5, color="white")
    ax.set_xticks(x, [LABEL[m] for m in models])
    ax.set_ylim(0, 105)
    ax.set_ylabel("Pass rate (%)", color=INK)
    ax.set_title("Exact rebuild of official Fama-French factors from raw CSVs\n"
                 "pass = script runs, >=95% months, RMSE <= 1 bp; bars show Wilson 95% CI",
                 fontsize=10, color=INK, loc="left")
    ax.legend(frameon=False, loc="upper right", ncol=2)
    style(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "pass_rate.png"))
    plt.close(fig)

    # ---------------- Figure 2: task heatmap ----------------
    cols = [(m, c) for m in models for c in conds]
    mat = np.full((len(tasks), len(cols)), np.nan)
    ann = [["" for _ in cols] for _ in tasks]
    for r in tp.itertuples():
        i, j = tasks.index(r.task), cols.index((r.model_alias, r.condition))
        mat[i, j] = r.pass_rate * 100
        ann[i][j] = f"{int(r.passed)}/{int(r.n)}"
    fig, ax = plt.subplots(figsize=(1.0 * len(cols) + 2.5, 0.5 * len(tasks) + 1.8), dpi=150)
    im = ax.imshow(mat, cmap="Blues", vmin=0, vmax=100, aspect="auto")
    for i in range(len(tasks)):
        for j in range(len(cols)):
            if ann[i][j]:
                ax.text(j, i, ann[i][j], ha="center", va="center", fontsize=8,
                        color="white" if mat[i, j] > 60 else INK)
    ax.set_xticks(range(len(cols)), [f"{LABEL[m]}\n{c.replace('_', ' ').lower()}" for m, c in cols],
                  fontsize=7.5)
    ax.set_yticks(range(len(tasks)), tasks, fontsize=9)
    ax.set_title("Pass rate by factor (cells: passed/runs)", fontsize=10, color=INK, loc="left")
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("pass rate (%)", color=MUTED)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "task_heatmap.png"))
    plt.close(fig)

    # ---------------- Figure 3: error tags ----------------
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=150)
    labels = [f"{LABEL[m]}\n{c.replace('_', ' ').lower()}" for m, c in cols]
    bottom = np.zeros(len(cols))
    present = [t for t in TAG_ORDER if t in tags.columns] + [t for t in tags.columns if t not in TAG_ORDER]
    for t in present:
        vals = np.array([tags.loc[(m, c), t] if (m, c) in tags.index else 0 for m, c in cols], dtype=float)
        ax.bar(range(len(cols)), vals, 0.7, bottom=bottom, label=t, color=TAG_COLOR.get(t, "#999999"),
               edgecolor="white", linewidth=1.5)
        bottom += vals
    ax.set_xticks(range(len(cols)), labels, fontsize=7.5)
    ax.set_ylabel("Failed runs (count)", color=INK)
    ax.set_title("Why runs failed (primary error tag)", fontsize=10, color=INK, loc="left")
    ax.legend(frameon=False, fontsize=7.5, bbox_to_anchor=(1.01, 1), loc="upper left")
    style(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "error_tags.png"))
    plt.close(fig)

    # ---------------- summary.md ----------------
    pr_show = pr.assign(pass_rate=(pr.pass_rate * 100).round(1),
                        ci=[f"[{lo * 100:.1f}, {hi * 100:.1f}]" for lo, hi in zip(pr.ci_low, pr.ci_high)])
    lines = [
        "# Factor Forge results" + (" (DRY RUN - fake model, not real results)" if a.dry_run else ""),
        "",
        f"Runs scored: {len(df)} (excluded {n_api} API errors). "
        f"PASS = script ran, coverage >= 95% of official months, RMSE <= 1 bp vs official series.",
        "",
        "## Pass rate by model and condition (Wilson 95% CI)",
        "",
        _table(pr_show[["model", "condition", "passed", "n", "pass_rate", "ci"]]),
        "",
        "## Fisher exact tests (two-sided; Holm-adjusted p across all rows)",
        "",
        _table(ft) if len(ft) else "(not enough groups)",
        "",
        "## Cost (USD) and latency",
        "",
        _table(cost.round(4)),
        "",
        "## Primary error tags among failed runs",
        "",
        _table(tags.reset_index()) if len(tags) else "(no failures)",
        "",
        "## Pass rate by task",
        "",
        _table(tp.pivot_table(index="task", columns=["model_alias", "condition"], values="pass_rate")
               .reindex(columns=pd.MultiIndex.from_tuples(cols)).round(2)
               .set_axis([f"{m}/{c}" for m, c in cols], axis=1).reset_index()),
        "",
        "Caveats: runs of the same task are not independent (task difficulty is shared), so the "
        "Fisher tests treat each run as independent and overstate precision; report per-task results "
        "alongside. Figures: figures/pass_rate.png, figures/task_heatmap.png, figures/error_tags.png.",
    ]
    with open(os.path.join(res_dir, "summary.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")

    pd.set_option("display.width", 200)
    print(pr_show[["model", "condition", "passed", "n", "pass_rate", "ci"]].to_string(index=False))
    print()
    print(ft.to_string(index=False, float_format=lambda v: f"{v:.4f}") if len(ft) else "")
    print()
    print(cost[cost.condition == "ALL"][["model", "runs", "passed", "total_cost_usd", "cost_per_correct_usd"]]
          .to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print(f"\nwrote {res_dir}/summary.md and 3 figures in {fig_dir}/")


def _table(d):
    """Plain markdown table without needing the 'tabulate' package."""
    d = d.copy()
    cols = [str(c) for c in d.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in d.itertuples(index=False):
        cells = []
        for v in row:
            if isinstance(v, float):
                cells.append("" if np.isnan(v) else (f"{v:.4g}" if abs(v) < 1e-3 and v != 0 else f"{v:.3f}".rstrip("0").rstrip(".")))
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


if __name__ == "__main__":
    main()
