# 06 - `score.py`

## In one sentence

`score.py` grades every finished run: it compares the script's `output.csv` with Ken French's official factor series, decides PASS or FAIL, labels each failure with a cause, and writes one row per run to `results/runs_scored.csv`.

## Why it exists

`run_experiment.py` only collects outputs. Something has to decide, the same way every time, whether each output is right. `score.py` is that judge.

It does two jobs:

1. **Pass/fail.** PASS means the script exited normally, covered at least 95% of the official months, and has RMSE at most 1.0 bp against the official series.
2. **Diagnosis.** For a failure, it tries to explain why: did the script crash? Did it flip the sign? Use the wrong table? Get the units wrong? These error tags make the results much more interesting than a bare pass rate.

## How to run it

From inside `~/letting-claude-cook/factor-forge` with the venv active:

```bash
python score.py              # scores runs/ into results/
python score.py --dry-run    # scores runs_dryrun/ into results_dryrun/
```

You can also pass `--runs FOLDER` and `--out FOLDER`. Scoring is quick and makes no API calls. You can rerun it any time; it rewrites `runs_scored.csv`.

Real output from scoring a 128-run dry run:

```
scored 128 runs from /.../factor-forge/runs_dryrun (PASS = ran, coverage >= 95%, RMSE <= 1.0 bp)
primary_tag
PASS                86
SIGN_FLIP            7
WRONG_BLOCK          6
BAD_FORMAT           6
DATE_MISALIGN        6
CRASH                4
NO_OUTPUT            4
NO_CODE              3
PARTIAL_COVERAGE     3
UNITS                2
WRONG_FORMULA        1

Dry-run check: planted variant (rows) vs scorer's primary tag (columns)
primary_tag       BAD_FORMAT  CRASH  DATE_MISALIGN  NO_CODE  NO_OUTPUT  PARTIAL_COVERAGE  PASS  SIGN_FLIP  UNITS  WRONG_BLOCK  WRONG_FORMULA
dry_run_variant                                                                                                                             
BAD_FORMAT                 6      0              0        0          0                 0     0          0      0            0              0
...
OK                         0      0              0        0          0                 0    86          0      0            0              0
...

0 mismatches

wrote /.../factor-forge/results_dryrun/runs_scored.csv
```

The "Dry-run check" table only appears for dry runs. Every number should sit on the diagonal (planted variant = scorer's tag), and the last line should say `0 mismatches`. For real runs you get only the first block and the `wrote` line.

## The error tags

| tag | meaning |
|---|---|
| PASS | correct |
| API_ERROR | the API call failed (an infrastructure problem, not the model's fault) |
| REFUSAL | the model refused |
| MAX_TOKENS | the reply hit the length limit before giving code |
| NO_CODE | the reply had no code block |
| TIMEOUT | the script ran longer than 60 s |
| CRASH | the script exited with an error |
| NO_OUTPUT | the script ran but wrote no `output.csv` |
| BAD_FORMAT | `output.csv` unreadable, wrong columns, or no YYYYMM dates |
| PARTIAL_COVERAGE | the numbers are right but fewer than 95% of months |
| SIGN_FLIP | matches the official series times -1 |
| UNITS | off by a factor of about 100 |
| WRONG_BLOCK | matches the equal-weighted version |
| DATE_MISALIGN | matches the official series shifted by one month |
| WRONG_FORMULA | none of the above; detail `SMB_SWAP` if it used the other SMB recipe |
| EXTRA_ROWS | secondary only: output also had non-monthly or duplicate rows |

A run can have several tags (stored in `tags`, separated by `;`). The first one is the `primary_tag`, used in the charts.

## Walkthrough

### Imports and constants

```python
import ground_truth as gt

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")
DIAG_TOL_BP = 2.0   # tolerance used when testing "does it match a known mistake?"
```

It reuses `ground_truth.py`'s parser and recipes (imported as `gt`). `DIAG_TOL_BP` is a looser tolerance (2 bp) used only when guessing which mistake explains a failure. Passing still requires 1 bp.

### `load_series(path)`

```python
    df = pd.read_csv(path)
    return pd.Series(df["value"].values, index=df["date"].astype(int).values, dtype=float)
```

Reads a `date,value` CSV into a pandas **Series**: one column of numbers, labeled by date. `.astype(int)` makes sure dates are integers like `192607`.

### `recompute(task_id, block_title)` - build the "wrong table" version

```python
    fn = gt.TASKS[task_id][0]
    saved = gt.VW
    try:
        gt.VW = block_title
        return fn(RAW)
    finally:
        gt.VW = saved
```

To recognize a WRONG_BLOCK mistake, the scorer needs to know what the factor looks like if built from the equal-weighted table. It reuses the correct recipe but temporarily changes `gt.VW` (the table title `ground_truth.py` reads) to `"Equal Weighted Returns -- Monthly"`.

`try ... finally` guarantees the `finally` part runs even if an error happens, so `gt.VW` is always put back.

Finance note: an equal-weighted portfolio gives every stock the same weight, so tiny stocks count as much as giant ones. Value-weighted portfolios weight by market cap. French's factors use value-weighted returns. Equal-weighted returns are correlated but noticeably different (the self-test shows about 137 bp RMSE for HML).

### `build_references(tasks)`

```python
        r = {"truth": load_series(os.path.join(HERE, t["truth_csv"])),
             "EW": recompute(tid, "Equal Weighted Returns -- Monthly")}
        if tid == "SMB_3F":
            r["SMB_SWAP"] = gt.smb_5f(RAW)
        if tid == "SMB_5F":
            r["SMB_SWAP"] = gt.smb_3f(RAW)
```

For each task it prepares: the official series (`truth`), the equal-weighted version (`EW`), and for the two SMB tasks, the other SMB recipe (`SMB_SWAP`). These are compared against each model output.

### `read_output(path)` - read the model's CSV carefully

```python
    try:
        df = pd.read_csv(path)
    except Exception as e:  # noqa: BLE001
        return None, 0, f"unreadable: {type(e).__name__}"
    df.columns = [str(c).strip().lower() for c in df.columns]
    if "date" not in df.columns or "value" not in df.columns:
        return None, 0, f"columns {list(df.columns)[:5]}"
```

Model output can be anything, so this is defensive. If pandas cannot read the file, it reports "unreadable". Column names are cleaned (spaces stripped, lower case), so `Date` or ` value` still count. If `date` or `value` is missing, that is a format problem.

```python
    date = pd.to_numeric(df["date"], errors="coerce")
    value = pd.to_numeric(df["value"], errors="coerce")
    monthly = date.notna() & (date == date.round()) & (date >= 100001) & (date <= 999912) \
        & ((date % 100) >= 1) & ((date % 100) <= 12)
```

`pd.to_numeric(..., errors="coerce")` turns text into numbers, and anything that is not a number (like `1926-07`) into NaN instead of crashing. `monthly` is a True/False mask for rows that look like real YYYYMM dates: a whole number, six digits, and the last two digits (`date % 100`, the remainder after dividing by 100) between 1 and 12. `&` combines conditions element by element. The backslash `\` continues the line.

```python
    s = pd.Series(value[monthly].values, index=date[monthly].astype(int).values)
    n_dup = int(s.index.duplicated().sum())
    s = s[~s.index.duplicated(keep="first")].dropna()
    n_extra = int((~monthly).sum()) + n_dup
```

Keeps only monthly rows. Duplicate dates keep the first occurrence. `~` means "not". Rows that are not monthly (for example annual rows like `1927` that a script read by mistake) and duplicates are counted as "extra rows". They are dropped for scoring and noted with the EXTRA_ROWS tag. If nothing usable is left, it reports "no YYYYMM monthly rows with numeric values". Otherwise it returns the series sorted by date.

### `compare(model, truth)` - the metrics

```python
    j = pd.concat([model.rename("m"), truth.rename("t")], axis=1, join="inner").dropna()
    if len(j) == 0:
        return dict(n_overlap=0, coverage=0.0, rmse_bp=np.nan, max_abs_bp=np.nan, corr=np.nan)
    err = j["m"] - j["t"]
```

Lines the two series up by date, keeping only months in both (`join="inner"`). Same metrics as in `ground_truth.py`:

- `n_overlap` - matched months.
- `coverage` - matched months divided by official months.
- `rmse_bp` - root mean squared error, times 100 to turn percent into basis points.
- `max_abs_bp` - worst single month.
- `corr` - correlation, only if there are more than 2 months and the model's series is not constant (otherwise correlation is undefined, so NaN).

`rmse_bp(a, b)` is a shortcut that returns just the RMSE.

### `shift_months(s, k)` - move dates by k months

```python
    idx = np.asarray(s.index, dtype=int)
    n = (idx // 100) * 12 + (idx % 100 - 1) + k          # months since year 0
    return pd.Series(s.values, index=(n // 12) * 100 + n % 12 + 1)
```

YYYYMM dates do not add like normal numbers (192612 + 1 is not a real month). So each date is converted to "months since year 0": year x 12 + (month - 1). Add `k`, then convert back. Example: 192612 is 1926 x 12 + 11. Add 1 and you get 1927 x 12 + 0, which converts back to 192701.

### `diagnose(m, refs, thr)` - which mistake is it?

This runs only for outputs that failed. It checks known mistakes in a fixed order and returns the first that fits.

```python
    tol = max(thr, DIAG_TOL_BP)
    c = compare(m, truth)
    if c["rmse_bp"] <= thr:
        return "PARTIAL_COVERAGE", f"coverage {c['coverage']:.1%}"
```

If the numbers are within 1 bp but the run still failed, the only reason left is coverage under 95%. `:.1%` formats 0.5 as `50.0%`.

```python
    if rmse_bp(-m, truth) <= tol or (c["corr"] == c["corr"] and c["corr"] < -0.9):
        return "SIGN_FLIP", f"corr {c['corr']:.3f}"
```

Flip the model's sign. If it now matches, or the correlation is below -0.9, it is a sign flip. (`c["corr"] == c["corr"]` is a trick to check "not NaN": NaN is the only value not equal to itself.) In finance terms, a sign flip means the model built the opposite portfolio (for example, long winners instead of long losers for a reversal factor).

```python
    for scale in (100.0, 0.01):
        if rmse_bp(m / scale, truth) <= tol:
            return "UNITS", f"x{scale:g}"
    ratio = m.abs().median() / max(truth.abs().median(), 1e-12)
    if 30 < ratio < 300 or 1 / 300 < ratio < 1 / 30:
        return "UNITS", f"scale ratio {ratio:.3g}"
```

Units: divide by 100 or by 0.01 and see if it matches. That catches a model that wrote 0.0123 for 1.23% or the reverse. As a backup, if the typical size of the model's numbers is 30 to 300 times bigger (or smaller) than the official ones, it is still a units problem even if other errors are mixed in. `max(..., 1e-12)` avoids dividing by zero.

```python
    ew = refs["EW"]
    if rmse_bp(m, ew) <= tol or rmse_bp(-m, ew) <= tol or compare(m, ew)["corr"] > 0.9999:
        return "WRONG_BLOCK", "matches equal-weighted table"
```

If it matches the equal-weighted version (or its sign flip, or correlates above 0.9999 with it), the script read the wrong table.

```python
    for k in (1, -1):
        if rmse_bp(shift_months(m, k), truth) <= tol:
            return "DATE_MISALIGN", f"shifted {k:+d} month"
    lag = compare(shift_months(m, 1), truth)["corr"]
    lead = compare(shift_months(m, -1), truth)["corr"]
    if max(lag, lead) > 0.95 and max(lag, lead) > c["corr"]:
        return "DATE_MISALIGN", f"lag corr {max(lag, lead):.3f}"
```

Shift the model's dates one month either way. If that fixes it, the dates were off by one. A looser version: if a shifted series correlates above 0.95 and better than the unshifted one, the dates are probably still off. `{k:+d}` prints the number with its sign (`+1` or `-1`).

```python
    if "SMB_SWAP" in refs and rmse_bp(m, refs["SMB_SWAP"]) <= tol:
        return "WRONG_FORMULA", "SMB_SWAP (used the other SMB definition)"
    return "WRONG_FORMULA", f"corr {c['corr']:.3f}"
```

For SMB, check whether it used the other SMB recipe. Otherwise it is a generic WRONG_FORMULA, and the detail records the correlation, which shows how close it got.

### `score_run(meta, run_dir, refs, rule)` - grade one run

```python
    thr, min_cov = rule["rmse_bp_max"], rule["min_coverage"]
    row = {k: meta.get(k) for k in (
        "run_key", "model_alias", "model_id", "task", "condition", "repeat", "dry_run", "effort",
```

Takes the threshold (1.0) and minimum coverage (0.95) from `tasks.json`. Copies useful fields from `meta.json` into the result row (`meta.get(k)` gives `None` if a key is missing) and adds blank metric fields.

The checks go from earliest failure to latest:

```python
    if meta.get("status") != "done":
        tags.append("API_ERROR")
    elif not meta.get("has_code"):
        if meta.get("stop_reason") == "refusal":
            tags.append("REFUSAL")
        elif meta.get("stop_reason") == "max_tokens":
            tags.append("MAX_TOKENS")
        else:
            tags.append("NO_CODE")
```

1. API call never finished: API_ERROR.
2. No code: REFUSAL, MAX_TOKENS or NO_CODE depending on why the model stopped.

```python
        row["script_ran"] = (meta.get("returncode") == 0) and not meta.get("timed_out")
        out_path = os.path.join(run_dir, "output.csv")
        if meta.get("timed_out"):
            tags.append("TIMEOUT")
        elif meta.get("returncode") != 0:
            tags.append("CRASH")
            detail = _last_error_line(run_dir)
```

3. There was code. Did it run? Timeout or crash get tagged. For a crash, the detail is the last line of `stderr.txt`, which is usually the error message (for example `RuntimeError: could not find the right table`).

```python
        if not os.path.exists(out_path):
            if not tags:
                tags.append("NO_OUTPUT")
        else:
            s, n_extra, problem = read_output(out_path)
```

4. No output file: NO_OUTPUT (unless already tagged crash or timeout). If there is an output file, it is still read and scored even after a crash, so you can see if the numbers were right.

```python
                    good = c["coverage"] >= min_cov and c["rmse_bp"] <= thr
                    row["passed"] = bool(row["script_ran"] and good)
                    if row["passed"]:
                        tags.append("PASS")
                    elif good:
                        pass   # numbers right but script crashed/timed out (tag already set)
                    else:
                        tag, d = diagnose(s, refs, thr)
```

5. Output readable: compute metrics. PASS needs both a clean run and good numbers. Good numbers after a crash still fail, and keep their CRASH or TIMEOUT tag (`pass` here is Python's "do nothing" statement, not a grade). Bad numbers go to `diagnose`. If the diagnosis is something else but coverage is also low, PARTIAL_COVERAGE is added as a second tag. EXTRA_ROWS is added if there were extra rows.

```python
    row.update(tags=";".join(tags), primary_tag=tags[0] if tags else "UNKNOWN", tag_detail=detail)
```

All tags are joined with `;`. The first is the primary tag.

### `_last_error_line(run_dir)`

Reads `stderr.txt`, drops blank lines, and returns the last line (up to 160 characters). In a Python traceback, the last line names the error.

### `main()`

```python
    for root, _, files in os.walk(runs):
        if "meta.json" in files:
```

`os.walk` visits every folder under `runs/`. Every folder that has a `meta.json` is one run, and gets scored with the references for its task.

```python
    df = pd.DataFrame(rows).sort_values(["model_alias", "task", "condition", "repeat"])
    df.to_csv(os.path.join(out, "runs_scored.csv"), index=False)
```

All rows become a DataFrame, sorted, saved. Then it prints the tag counts (`value_counts()` counts how often each value appears).

```python
    if df["dry_run_variant"].notna().any():
        ...
        check = pd.crosstab(df["dry_run_variant"], df["primary_tag"])
```

Only for dry runs (where the planted variant is known). `pd.crosstab` builds a count table: planted variant down the side, scorer's tag across the top. It saves that to `dryrun_check.csv`, prints it, and lists any mismatches.

## What `runs_scored.csv` contains

One row per run with these columns (real header):

```
run_key,model_alias,model_id,task,condition,repeat,dry_run,effort,status,stop_reason,refusal_category,input_tokens,output_tokens,cost_usd,latency_s,has_code,n_code_blocks,returncode,timed_out,script_runtime_s,has_output,prompt_sha,dry_run_variant,n_overlap,coverage,rmse_bp,max_abs_bp,corr,n_extra_rows,script_ran,passed,tags,primary_tag,tag_detail
```

## If something goes wrong

- **`no runs found in .../runs`** - nothing has been run yet, or you meant the dry-run folder. Add `--dry-run`, or run `run_experiment.py` first.
- **`KeyError: 'SOMETASK'`** - a run folder holds a task that is not in `tasks.json` (for example, an old test). Move that folder out of `runs/`.
- **Dry-run check shows mismatches** - the scorer mislabels something. Run `python selftest.py` to see exactly which task and variant, and fix `diagnose()` before scoring real runs.
- **Everything is WRONG_BLOCK or UNITS, even good-looking scripts** - `data/truth/` may be stale or from a different data release. Rerun `ground_truth.py` and confirm its RMSEs are under 0.5 bp.

## Check your understanding

1. A script exits with an error but still wrote a perfect `output.csv`. Does it pass, and what is its primary tag?
2. Why does `diagnose` check PARTIAL_COVERAGE first?
3. Why can't you shift YYYYMM dates by just adding 1?

<details>
<summary>Answers</summary>

1. No. PASS requires the script to have run cleanly. The primary tag is CRASH. Its metrics are still recorded, so you can see the numbers were right.
2. Because if the RMSE is already within 1 bp, the numbers are correct, so the only possible reason for failing is low coverage. No other mistake needs to be tested.
3. Because 192612 + 1 = 192613, which is not a month. The code converts to "months since year 0", adds, and converts back, so December 1926 + 1 becomes 192701.

</details>
