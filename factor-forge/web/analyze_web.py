"""
Form Forge -- analysis: tables, statistics and figures (H1-H5 of docs/06).

Input : <in>  results_web/runs_scored.csv          (from score_web.py)
        <part2> results/runs_scored.csv            (optional: Part 2, for H1)
Output: <out>/pass_rates.csv      Wilson 95% CIs: overall, by model, condition, task, model x condition
        <out>/fisher_tests.csv    H1 Part 2 vs Part 3; H2 Fable vs Haiku, Opus vs Sonnet (+ adjacent models);
                                  H3 STEPS vs GOAL_ONLY pooled and per model; Holm-adjusted
        <out>/error_tags.csv      model x tag and condition x tag counts (failed runs)
        <out>/efficiency.csv      steps per successful run (median, IQR), tokens, $ per correct answer
        <out>/behavior.csv        share of runs that tried a blocked URL / used the search form
        <out>/summary.md          everything above + the Part 2 vs Part 3 table
        <out>/fig_task_heatmap.png, fig_cost_per_correct.png, fig_steps_success.png

    python web/analyze_web.py --in results_web/runs_scored.csv --part2 results/runs_scored.csv --out results_web
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, PROJECT)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import fisher_exact  # noqa: E402

from analyze import GRID, INK, MUTED, _table, style, wilson  # noqa: E402  (Part 2 helpers + palette)
from run_experiment import MODEL_ORDER  # noqa: E402
from score_web import FINANCE_NAV_TAGS  # noqa: E402

BAR = "#2a78d6"            # single-series color (slot 1 of the project palette)
CONDS = ["STEPS", "GOAL_ONLY"]


def rate_rows(df, group_cols, label):
    rows = []
    groups = [((), df)] if not group_cols else df.groupby(group_cols, sort=False)
    for keys, g in groups:
        keys = keys if isinstance(keys, tuple) else (keys,)
        k, n = int(g.passed.sum()), len(g)
        lo, hi = wilson(k, n)
        rows.append(dict(grouping=label, group=" / ".join(map(str, keys)) or "all", passed=k, n=n,
                         pass_rate=k / n if n else np.nan, ci_low=lo, ci_high=hi))
    return rows


def main():
    ap = argparse.ArgumentParser(description="Form Forge tables and figures")
    ap.add_argument("--in", dest="inp", default=os.path.join(PROJECT, "results_web", "runs_scored.csv"))
    ap.add_argument("--part2", default=None, help="Part 2 results/runs_scored.csv (for H1)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = a.out or os.path.dirname(os.path.abspath(a.inp))
    os.makedirs(out, exist_ok=True)

    df = pd.read_csv(a.inp)
    n_harness = int((df.primary_tag == "HARNESS_ERROR").sum())
    df = df[df.primary_tag != "HARNESS_ERROR"].copy()      # site/harness problems are not model failures
    df["passed"] = df["passed"].astype(bool)
    dry = bool(df["dry_run"].fillna(False).astype(bool).any())
    present = list(dict.fromkeys(df.model_alias))
    models = [m for m in MODEL_ORDER if m in present] + sorted(m for m in present if m not in MODEL_ORDER)
    conds = [c for c in CONDS if c in set(df.condition)]
    tasks = sorted(set(df.task), key=lambda t: int(t[1:]))

    # ---------------- 1. pass rates with Wilson CIs ----------------
    rows = rate_rows(df, [], "overall") + rate_rows(df, ["model_alias"], "model") \
        + rate_rows(df, ["condition"], "condition") + rate_rows(df, ["task"], "task") \
        + rate_rows(df, ["model_alias", "condition"], "model x condition")
    pr = pd.DataFrame(rows)
    pr.to_csv(os.path.join(out, "pass_rates.csv"), index=False)

    # ---------------- 2. Fisher exact tests ----------------
    tests = []

    def fisher(hyp, label, k1, n1, k2, n2):
        if n1 and n2:
            _, p = fisher_exact([[k1, n1 - k1], [k2, n2 - k2]])
            tests.append(dict(hypothesis=hyp, comparison=label, a=f"{k1}/{n1}", b=f"{k2}/{n2}", p_value=p))

    def kn(g):
        return int(g.passed.sum()), len(g)

    if a.part2 and os.path.exists(a.part2):
        p2 = pd.read_csv(a.part2)
        p2 = p2[p2.primary_tag != "API_ERROR"]
        p2["passed"] = p2["passed"].astype(bool)
        fisher("H1", "all models: Part 2 vs Part 3", *kn(p2), *kn(df))
        for m in models:
            if m in set(p2.model_alias):
                fisher("H1", f"{m}: Part 2 vs Part 3", *kn(p2[p2.model_alias == m]), *kn(df[df.model_alias == m]))
    else:
        p2 = None
    pairs = [("fable", "haiku"), ("opus", "sonnet")] + list(zip(models, models[1:]))
    for m1, m2 in dict.fromkeys(pairs):
        if m1 in models and m2 in models:
            fisher("H2", f"{m1} vs {m2}", *kn(df[df.model_alias == m1]), *kn(df[df.model_alias == m2]))
    if len(conds) == 2:
        fisher("H3", "all models: STEPS vs GOAL_ONLY", *kn(df[df.condition == "STEPS"]),
               *kn(df[df.condition == "GOAL_ONLY"]))
        for m in models:
            g = df[df.model_alias == m]
            fisher("H3", f"{m}: STEPS vs GOAL_ONLY", *kn(g[g.condition == "STEPS"]), *kn(g[g.condition == "GOAL_ONLY"]))
    ft = pd.DataFrame(tests)
    if len(ft):
        order = ft["p_value"].sort_values().index
        running = 0.0
        for i, idx in enumerate(order):
            running = max(running, min(1.0, (len(ft) - i) * ft.loc[idx, "p_value"]))
            ft.loc[idx, "p_holm"] = running
    ft.to_csv(os.path.join(out, "fisher_tests.csv"), index=False)

    # ---------------- 3. error tags (H4) ----------------
    fails = df[~df.passed]
    tag_m = pd.crosstab(fails.model_alias, fails.primary_tag) if len(fails) else pd.DataFrame()
    tag_c = pd.crosstab(fails.condition, fails.primary_tag) if len(fails) else pd.DataFrame()
    with open(os.path.join(out, "error_tags.csv"), "w") as fh:
        fh.write("# model x tag\n")
        tag_m.to_csv(fh)
        fh.write("# condition x tag\n")
        tag_c.to_csv(fh)
    share_fin = fails.primary_tag.isin(FINANCE_NAV_TAGS).mean() if len(fails) else np.nan

    # ---------------- 4. efficiency (H5) ----------------
    eff = []
    for m in models:
        g = df[df.model_alias == m]
        s = g[g.passed].steps
        k = int(g.passed.sum())
        total = float(g.cost_usd.sum())
        tok = g.input_tokens + g.cache_read_input_tokens + g.cache_creation_input_tokens
        eff.append(dict(model=m, runs=len(g), passed=k, median_steps_success=s.median() if k else np.nan,
                        iqr_steps_success=(s.quantile(.75) - s.quantile(.25)) if k else np.nan,
                        mean_prompt_tokens=tok.mean(), mean_output_tokens=g.output_tokens.mean(),
                        cache_read_share=(g.cache_read_input_tokens.sum() / tok.sum()) if tok.sum() else np.nan,
                        total_cost_usd=total, cost_per_correct_usd=total / k if k else np.nan,
                        median_wall_s=g.wall_s.median()))
    eff = pd.DataFrame(eff)
    eff.to_csv(os.path.join(out, "efficiency.csv"), index=False)

    # ---------------- 5. behavior ----------------
    beh = (df.assign(tried_blocked=df.blocked_attempts.fillna(0) > 0,
                     used_search_form=df.visited_search_form.fillna(False).astype(bool))
           .groupby(["model_alias", "condition"])[["tried_blocked", "used_search_form"]].mean().reset_index())
    beh.to_csv(os.path.join(out, "behavior.csv"), index=False)

    # ---------------- Figure 1: task x model heatmap (pass counts) ----------------
    cols = models
    mat = np.full((len(tasks), len(cols)), np.nan)
    ann = [["" for _ in cols] for _ in tasks]
    for (t, m), g in df.groupby(["task", "model_alias"]):
        i, j = tasks.index(t), cols.index(m)
        mat[i, j] = g.passed.mean() * 100
        ann[i][j] = f"{int(g.passed.sum())}/{len(g)}"
    fig, ax = plt.subplots(figsize=(1.1 * len(cols) + 2.4, 0.5 * len(tasks) + 1.8), dpi=150)
    im = ax.imshow(mat, cmap="Blues", vmin=0, vmax=100, aspect="auto")
    for i in range(len(tasks)):
        for j in range(len(cols)):
            if ann[i][j]:
                ax.text(j, i, ann[i][j], ha="center", va="center", fontsize=8,
                        color="white" if mat[i, j] > 60 else INK)
    ax.set_xticks(range(len(cols)), cols, fontsize=8, rotation=30 if dry else 0, ha="right" if dry else "center")
    ax.set_yticks(range(len(tasks)), tasks, fontsize=9)
    ax.set_title("Form Forge: passes per task and model (cells: passed/runs)", fontsize=10, color=INK, loc="left")
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("pass rate (%)", color=MUTED)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_task_heatmap.png"))
    plt.close(fig)

    # ---------------- Figure 2: cost per correct answer ----------------
    fig, ax = plt.subplots(figsize=(7, 3.8), dpi=150)
    e = eff.set_index("model").reindex(models)
    vals = e.cost_per_correct_usd.fillna(0).values
    ax.bar(range(len(models)), vals, 0.6, color=BAR, edgecolor="white", linewidth=2)
    for i, (v, r) in enumerate(zip(vals, e.itertuples())):
        ax.text(i, v, f"\\${v:.3f}\n{r.passed}/{r.runs} pass" if r.passed else "no passes", ha="center", va="bottom",
                fontsize=7.5, color=INK)
    ax.set_xticks(range(len(models)), models, fontsize=8, rotation=30 if dry else 0, ha="right" if dry else "center")
    ax.set_ylabel("\\$ per correct answer", color=INK)
    ax.set_title("Cost per correct answer (total \\$ / passes)" + ("  [DRY RUN: fake \\$]" if dry else ""),
                 fontsize=10, color=INK, loc="left")
    ax.set_ylim(0, max(vals.max() * 1.3, 1e-6))
    style(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_cost_per_correct.png"))
    plt.close(fig)

    # ---------------- Figure 3: steps per successful run ----------------
    fig, ax = plt.subplots(figsize=(7, 3.8), dpi=150)
    data = [df[(df.model_alias == m) & df.passed].steps.values for m in models]
    keep = [i for i, d in enumerate(data) if len(d)]
    if keep:
        bp = ax.boxplot([data[i] for i in keep], positions=keep, widths=0.5, patch_artist=True,
                        medianprops=dict(color=INK, linewidth=1.5), whiskerprops=dict(color=MUTED),
                        capprops=dict(color=MUTED), flierprops=dict(marker="o", markersize=4,
                                                                    markerfacecolor=BAR, markeredgecolor="white"))
        for b in bp["boxes"]:
            b.set(facecolor=BAR + "55", edgecolor=BAR, linewidth=1.2)
    ax.set_xticks(range(len(models)), models, fontsize=8, rotation=30 if dry else 0, ha="right" if dry else "center")
    ax.set_xlim(-0.6, len(models) - 0.4)
    ax.set_ylim(0, max([d.max() for d in data if len(d)] + [1]) + 2)
    ax.set_ylabel("tool calls", color=INK)
    ax.set_title("Tool calls per successful run", fontsize=10, color=INK, loc="left")
    style(ax)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_steps_success.png"))
    plt.close(fig)

    # ---------------- summary.md ----------------
    show = pr.assign(pass_rate=(pr.pass_rate * 100).round(1),
                     ci=[f"[{lo * 100:.1f}, {hi * 100:.1f}]" for lo, hi in zip(pr.ci_low, pr.ci_high)])
    p2rows = []
    if p2 is not None:
        for m in models:
            g2, g3 = p2[p2.model_alias == m], df[df.model_alias == m]
            if len(g2):
                p2rows.append(dict(model=m, part2=f"{int(g2.passed.sum())}/{len(g2)}",
                                   part3=f"{int(g3.passed.sum())}/{len(g3)}",
                                   part2_cost=round(g2.cost_usd.sum(), 2), part3_cost=round(g3.cost_usd.sum(), 2)))
        p2rows.append(dict(model="ALL", part2=f"{int(p2.passed.sum())}/{len(p2)}",
                           part3=f"{int(df.passed.sum())}/{len(df)}", part2_cost=round(p2.cost_usd.sum(), 2),
                           part3_cost=round(df.cost_usd.sum(), 2)))
    lines = [
        "# Form Forge (Part 3) results" + (" -- DRY RUN (mock personas, fake $), NOT real results" if dry else ""),
        "",
        f"Runs scored: {len(df)} (excluded {n_harness} HARNESS_ERROR runs). PASS = answered, exact whole-dollar "
        "value, original accession (T8: four exact values + exact ranking).",
        "",
        "## Part 2 vs Part 3 (the headline table)",
        "",
        _table(pd.DataFrame(p2rows)) if p2rows else "(no Part 2 file given: pass --part2 results/runs_scored.csv)",
        "",
        "## Pass rates (Wilson 95% CI)",
        "",
        _table(show[["grouping", "group", "passed", "n", "pass_rate", "ci"]]),
        "",
        "## Fisher exact tests (two-sided; Holm-adjusted across all rows)",
        "",
        _table(ft) if len(ft) else "(not enough groups)",
        "",
        "## Error tags among failed runs (H4)",
        "",
        _table(tag_m.reset_index()) if len(tag_m) else "(no failures)",
        "",
        f"Share of failures that are finance/navigation mistakes ({', '.join(FINANCE_NAV_TAGS)}): "
        + (f"{share_fin:.0%}" if share_fin == share_fin else "n/a"),
        "",
        "## Efficiency and cost (H5)",
        "",
        _table(eff.round(4)),
        "",
        "## Behavior",
        "",
        _table(beh.round(3)),
        "",
        "Caveats: runs of one task share its difficulty, so treating runs as independent overstates precision; "
        "report per-task results alongside. The live site can change between runs (new filings); the run order is "
        "repeat-major so any change hits all models equally.",
    ]
    with open(os.path.join(out, "summary.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")

    pd.set_option("display.width", 200)
    print(show[show.grouping.isin(["overall", "model", "condition"])][["grouping", "group", "passed", "n",
                                                                     "pass_rate", "ci"]].to_string(index=False))
    print()
    print(ft.to_string(index=False, float_format=lambda v: f"{v:.4f}") if len(ft) else "(no Fisher tests)")
    print()
    print(eff[["model", "runs", "passed", "median_steps_success", "total_cost_usd", "cost_per_correct_usd"]]
          .to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print(f"\nshare of failures in finance/navigation tags: {share_fin:.0%}" if share_fin == share_fin else "")
    print(f"wrote {out}/summary.md, 5 CSVs and 3 figures")


if __name__ == "__main__":
    main()
