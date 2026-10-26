"""
Factor Forge -- automatic scorer.

Reads every finished run in runs/ (or runs_dryrun/ with --dry-run), compares the
script's output.csv to Ken French's OFFICIAL factor series (data/truth/), and
writes one row per run to results/runs_scored.csv.

Metrics (on months present in both series):
  coverage    = matched months / official months
  rmse_bp     = root-mean-square error in basis points (1 bp = 0.01 percentage point)
  max_abs_bp  = largest single-month error in bp
  corr        = Pearson correlation

PASS = script exited normally AND coverage >= 95% AND rmse_bp <= threshold
(threshold comes from tasks.json: max(1 bp, 2 x worst human-reference RMSE) = 1.0 bp).

Error tags (primary_tag = the first one; all tags are kept in `tags`):
  API_ERROR, REFUSAL, MAX_TOKENS, NO_CODE  -- the model never gave runnable code
  TIMEOUT, CRASH                           -- script failed (CRASH = nonzero exit)
  NO_OUTPUT                                -- script ran but wrote no output.csv
  BAD_FORMAT                               -- output.csv unreadable / wrong columns / no YYYYMM dates
  PARTIAL_COVERAGE                         -- numbers right but < 95% of months
  SIGN_FLIP                                -- matches official x (-1)
  UNITS                                    -- off by a factor of ~100
  WRONG_BLOCK                              -- matches the EQUAL-weighted recomputation
  DATE_MISALIGN                            -- matches official shifted by +/- 1 month
  WRONG_FORMULA                            -- none of the above (detail SMB_SWAP if it used the other SMB recipe)
  EXTRA_ROWS (secondary only)              -- output also had non-monthly or duplicate rows
"""
import argparse
import json
import os

import numpy as np
import pandas as pd

import ground_truth as gt

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")
DIAG_TOL_BP = 2.0   # tolerance used when testing "does it match a known mistake?"


# ---------------------------------------------------------------------------
# Reference series: the truth, plus known-wrong variants used for diagnosis
# ---------------------------------------------------------------------------
def load_series(path):
    df = pd.read_csv(path)
    return pd.Series(df["value"].values, index=df["date"].astype(int).values, dtype=float)


def recompute(task_id, block_title):
    """Rebuild a factor with ground_truth.py's recipe, but from a different table block.

    ground_truth's helper _p() reads the global gt.VW (the block title) each time it
    is called, so we swap it temporarily and put it back afterwards.
    """
    fn = gt.TASKS[task_id][0]
    saved = gt.VW
    try:
        gt.VW = block_title
        return fn(RAW)
    finally:
        gt.VW = saved


def build_references(tasks):
    refs = {}
    for t in tasks:
        tid = t["id"]
        r = {"truth": load_series(os.path.join(HERE, t["truth_csv"])),
             "EW": recompute(tid, "Equal Weighted Returns -- Monthly")}
        if tid == "SMB_3F":
            r["SMB_SWAP"] = gt.smb_5f(RAW)
        if tid == "SMB_5F":
            r["SMB_SWAP"] = gt.smb_3f(RAW)
        refs[tid] = r
    return refs


# ---------------------------------------------------------------------------
# Reading the model's output.csv
# ---------------------------------------------------------------------------
def read_output(path):
    """Return (series indexed by int YYYYMM, n_extra_rows, problem or None)."""
    try:
        df = pd.read_csv(path)
    except Exception as e:  # noqa: BLE001
        return None, 0, f"unreadable: {type(e).__name__}"
    df.columns = [str(c).strip().lower() for c in df.columns]
    if "date" not in df.columns or "value" not in df.columns:
        return None, 0, f"columns {list(df.columns)[:5]}"
    date = pd.to_numeric(df["date"], errors="coerce")
    value = pd.to_numeric(df["value"], errors="coerce")
    monthly = date.notna() & (date == date.round()) & (date >= 100001) & (date <= 999912) \
        & ((date % 100) >= 1) & ((date % 100) <= 12)
    s = pd.Series(value[monthly].values, index=date[monthly].astype(int).values)
    n_dup = int(s.index.duplicated().sum())
    s = s[~s.index.duplicated(keep="first")].dropna()
    n_extra = int((~monthly).sum()) + n_dup
    if len(s) == 0:
        return None, n_extra, "no YYYYMM monthly rows with numeric values"
    return s.sort_index(), n_extra, None


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def compare(model, truth):
    j = pd.concat([model.rename("m"), truth.rename("t")], axis=1, join="inner").dropna()
    if len(j) == 0:
        return dict(n_overlap=0, coverage=0.0, rmse_bp=np.nan, max_abs_bp=np.nan, corr=np.nan)
    err = j["m"] - j["t"]
    corr = j["m"].corr(j["t"]) if len(j) > 2 and j["m"].std() > 0 else np.nan
    return dict(n_overlap=len(j), coverage=len(j) / truth.notna().sum(),
                rmse_bp=float(np.sqrt((err ** 2).mean()) * 100),
                max_abs_bp=float(err.abs().max() * 100), corr=float(corr))


def rmse_bp(a, b):
    return compare(a, b)["rmse_bp"]


def shift_months(s, k):
    """Move every YYYYMM date k months later (k may be negative)."""
    idx = np.asarray(s.index, dtype=int)
    n = (idx // 100) * 12 + (idx % 100 - 1) + k          # months since year 0
    return pd.Series(s.values, index=(n // 12) * 100 + n % 12 + 1)


def diagnose(m, refs, thr):
    """Which known mistake explains this (wrong) series? Returns (tag, detail)."""
    truth = refs["truth"]
    tol = max(thr, DIAG_TOL_BP)
    c = compare(m, truth)
    if c["rmse_bp"] <= thr:
        return "PARTIAL_COVERAGE", f"coverage {c['coverage']:.1%}"
    if rmse_bp(-m, truth) <= tol or (c["corr"] == c["corr"] and c["corr"] < -0.9):
        return "SIGN_FLIP", f"corr {c['corr']:.3f}"
    for scale in (100.0, 0.01):
        if rmse_bp(m / scale, truth) <= tol:
            return "UNITS", f"x{scale:g}"
    ratio = m.abs().median() / max(truth.abs().median(), 1e-12)
    if 30 < ratio < 300 or 1 / 300 < ratio < 1 / 30:
        return "UNITS", f"scale ratio {ratio:.3g}"
    ew = refs["EW"]
    if rmse_bp(m, ew) <= tol or rmse_bp(-m, ew) <= tol or compare(m, ew)["corr"] > 0.9999:
        return "WRONG_BLOCK", "matches equal-weighted table"
    for k in (1, -1):
        if rmse_bp(shift_months(m, k), truth) <= tol:
            return "DATE_MISALIGN", f"shifted {k:+d} month"
    lag = compare(shift_months(m, 1), truth)["corr"]
    lead = compare(shift_months(m, -1), truth)["corr"]
    if max(lag, lead) > 0.95 and max(lag, lead) > c["corr"]:
        return "DATE_MISALIGN", f"lag corr {max(lag, lead):.3f}"
    if "SMB_SWAP" in refs and rmse_bp(m, refs["SMB_SWAP"]) <= tol:
        return "WRONG_FORMULA", "SMB_SWAP (used the other SMB definition)"
    return "WRONG_FORMULA", f"corr {c['corr']:.3f}"


def score_run(meta, run_dir, refs, rule):
    thr, min_cov = rule["rmse_bp_max"], rule["min_coverage"]
    row = {k: meta.get(k) for k in (
        "run_key", "model_alias", "model_id", "task", "condition", "repeat", "dry_run", "effort",
        "status", "stop_reason", "refusal_category", "input_tokens", "output_tokens", "cost_usd",
        "latency_s", "has_code", "n_code_blocks", "returncode", "timed_out", "script_runtime_s",
        "has_output", "prompt_sha", "dry_run_variant")}
    row.update(n_overlap=0, coverage=0.0, rmse_bp=np.nan, max_abs_bp=np.nan, corr=np.nan,
               n_extra_rows=0, script_ran=False, passed=False, tags="", primary_tag="", tag_detail="")
    tags, detail = [], ""

    if meta.get("status") != "done":
        tags.append("API_ERROR")
        detail = str(meta.get("error", ""))[:120]
    elif not meta.get("has_code"):
        if meta.get("stop_reason") == "refusal":
            tags.append("REFUSAL")
            detail = str(meta.get("refusal_category"))
        elif meta.get("stop_reason") == "max_tokens":
            tags.append("MAX_TOKENS")
        else:
            tags.append("NO_CODE")
    else:
        row["script_ran"] = (meta.get("returncode") == 0) and not meta.get("timed_out")
        out_path = os.path.join(run_dir, "output.csv")
        if meta.get("timed_out"):
            tags.append("TIMEOUT")
        elif meta.get("returncode") != 0:
            tags.append("CRASH")
            detail = _last_error_line(run_dir)
        if not os.path.exists(out_path):
            if not tags:
                tags.append("NO_OUTPUT")
        else:
            s, n_extra, problem = read_output(out_path)
            row["n_extra_rows"] = n_extra
            if problem:
                tags.append("BAD_FORMAT")
                detail = detail or problem
            else:
                c = compare(s, refs["truth"])
                row.update(c)
                if c["n_overlap"] == 0:
                    tags.append("BAD_FORMAT")
                    detail = detail or "no dates overlap the official series"
                else:
                    good = c["coverage"] >= min_cov and c["rmse_bp"] <= thr
                    row["passed"] = bool(row["script_ran"] and good)
                    if row["passed"]:
                        tags.append("PASS")
                    elif good:
                        pass   # numbers right but script crashed/timed out (tag already set)
                    else:
                        tag, d = diagnose(s, refs, thr)
                        tags.append(tag)
                        detail = detail or d
                        if tag != "PARTIAL_COVERAGE" and c["coverage"] < min_cov:
                            tags.append("PARTIAL_COVERAGE")
                if n_extra:
                    tags.append("EXTRA_ROWS")
    if meta.get("stop_reason") == "max_tokens" and "MAX_TOKENS" not in tags:
        tags.append("MAX_TOKENS")
    row.update(tags=";".join(tags), primary_tag=tags[0] if tags else "UNKNOWN", tag_detail=detail)
    return row


def _last_error_line(run_dir):
    p = os.path.join(run_dir, "stderr.txt")
    if not os.path.exists(p):
        return ""
    lines = [ln for ln in open(p).read().splitlines() if ln.strip()]
    return lines[-1][:160] if lines else ""


def main():
    ap = argparse.ArgumentParser(description="Score all finished runs against the official factors.")
    ap.add_argument("--dry-run", action="store_true", help="score runs_dryrun/ into results_dryrun/")
    ap.add_argument("--runs", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    runs = a.runs or os.path.join(HERE, "runs_dryrun" if a.dry_run else "runs")
    out = a.out or os.path.join(HERE, "results_dryrun" if a.dry_run else "results")
    os.makedirs(out, exist_ok=True)

    with open(os.path.join(HERE, "tasks.json")) as fh:
        doc = json.load(fh)
    rule = doc["pass_rule"]
    refs = build_references(doc["tasks"])

    rows = []
    for root, _, files in os.walk(runs):
        if "meta.json" in files:
            with open(os.path.join(root, "meta.json")) as fh:
                meta = json.load(fh)
            rows.append(score_run(meta, root, refs[meta["task"]], rule))
    if not rows:
        raise SystemExit(f"no runs found in {runs}")
    df = pd.DataFrame(rows).sort_values(["model_alias", "task", "condition", "repeat"])
    df.to_csv(os.path.join(out, "runs_scored.csv"), index=False)

    print(f"scored {len(df)} runs from {runs} (PASS = ran, coverage >= {rule['min_coverage']:.0%}, "
          f"RMSE <= {rule['rmse_bp_max']} bp)")
    print(df["primary_tag"].value_counts().to_string())

    # In a dry run we KNOW which mistake each fake script made: check the tags agree.
    if df["dry_run_variant"].notna().any():
        expect = {"OK": "PASS"}
        df["expected_tag"] = df["dry_run_variant"].map(lambda v: expect.get(v, v))
        check = pd.crosstab(df["dry_run_variant"], df["primary_tag"])
        check.to_csv(os.path.join(out, "dryrun_check.csv"))
        bad = df[df["expected_tag"] != df["primary_tag"]]
        print("\nDry-run check: planted variant (rows) vs scorer's primary tag (columns)")
        print(check.to_string())
        print(f"\n{len(bad)} mismatches" + ("" if bad.empty else ":\n" + bad[
            ["run_key", "dry_run_variant", "primary_tag", "tag_detail"]].to_string(index=False)))
    print(f"\nwrote {os.path.join(out, 'runs_scored.csv')}")


if __name__ == "__main__":
    main()
