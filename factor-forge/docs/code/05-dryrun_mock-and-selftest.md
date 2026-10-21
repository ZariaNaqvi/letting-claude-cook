# 05 - `dryrun_mock.py` and `selftest.py`

## In one sentence

`dryrun_mock.py` is a fake model that returns correct or deliberately broken scripts, and `selftest.py` uses it to plant every known mistake on every task and check that the scorer catches each one.

## Why they exist

Before you spend money on 320 real API calls, you want proof that the pipeline works and that the scorer is right. Two risks:

1. The harness could have a bug (wrong folder, file not copied, output lost).
2. The scorer could mislabel mistakes. For example, it could call a sign error a "wrong formula", or pass a script it should fail.

The fix is to test with answers you already know. `dryrun_mock.py` writes scripts where you know the exact mistake, because you planted it. If the scorer's tag matches the planted mistake every time, you can trust its tags on real model output.

- `run_experiment.py --dry-run` uses the mock to fill `runs_dryrun/` with fake runs (about 70% correct, 30% broken at random). Then `score.py --dry-run` and `analyze.py --dry-run` run on them, testing the whole pipeline end to end.
- `selftest.py` is more systematic: it forces every mistake on every task.

The mock contains working solutions. Its docstring says it is never shown to the models. It is only imported in dry-run mode and by the self-test.

## How to run them

From inside `~/letting-claude-cook/factor-forge` with the venv active:

```bash
python selftest.py
```

It takes about a minute and calls no API. Real output (shortened):

```
ok  HML     OK                -> PASS              rmse=0.29bp cov=1.00 
ok  HML     SIGN_FLIP         -> SIGN_FLIP         rmse=713.64bp cov=1.00 corr -1.000
ok  HML     WRONG_BLOCK       -> WRONG_BLOCK       rmse=137.34bp cov=1.00 matches equal-weighted table
ok  HML     UNITS             -> UNITS             rmse=35324.88bp cov=1.00 x100
ok  HML     DATE_MISALIGN     -> DATE_MISALIGN     rmse=450.26bp cov=1.00 shifted -1 month
ok  HML     PARTIAL_COVERAGE  -> PARTIAL_COVERAGE  rmse=0.29bp cov=0.50 coverage 50.0%
ok  HML     WRONG_FORMULA     -> WRONG_FORMULA     rmse=160.92bp cov=1.00 corr 0.903
ok  HML     CRASH             -> CRASH             rmse=nanbp cov=0.00 RuntimeError: could not find the right table
ok  HML     NO_OUTPUT         -> NO_OUTPUT         rmse=nanbp cov=0.00 
ok  HML     BAD_FORMAT        -> BAD_FORMAT        rmse=nanbp cov=0.00 no YYYYMM monthly rows with numeric values
ok  HML     NO_CODE           -> NO_CODE           rmse=nanbp cov=0.00 
ok  SMB_3F  OK                -> PASS              rmse=0.30bp cov=1.00 
...
ok  HML     TIMEOUT           -> TIMEOUT
ok  API key hidden from model script

90/90 checks passed
```

Each line: `ok` (or `BAD`), the task, the planted mistake, the tag the scorer gave, the RMSE, the coverage, and the scorer's detail note. 90 checks = 8 tasks x 11 variants (OK plus 10 mistakes) + 1 timeout check + 1 API-key check. The program exits with code 0 if all pass and 1 if any fail.

Note the DATE_MISALIGN detail says "shifted -1 month". The mock moves every date one month later. The scorer finds that shifting the model's series one month earlier (-1) fixes it.

There is no command for `dryrun_mock.py` on its own. It is used through:

```bash
python run_experiment.py --dry-run --repeats 2
python score.py --dry-run
python analyze.py --dry-run
```

## Walkthrough of `dryrun_mock.py`

### The planted mistakes

The docstring lists 11 variants:

| variant | what the fake script does wrong |
|---|---|
| OK | nothing; correct script |
| SIGN_FLIP | multiplies the right answer by -1 |
| WRONG_BLOCK | reads the equal-weighted table instead of value-weighted |
| UNITS | multiplies by 100 (decimal vs percent confusion) |
| DATE_MISALIGN | dates shifted by one month |
| PARTIAL_COVERAGE | writes only the second half of the months |
| WRONG_FORMULA | a plausible but wrong recipe |
| CRASH | raises an exception |
| NO_OUTPUT | runs but writes `factor.csv` instead of `output.csv` |
| BAD_FORMAT | writes dates like `1926-07` instead of `192607` |
| NO_CODE | reply has no code block |

These are the mistakes a real model is likely to make, so they are also the scorer's error tags.

### Recipes as weights

```python
def _hl(f, hi_s, hi_b, lo_s, lo_b):
    return [(f, {hi_s: 0.5, hi_b: 0.5, lo_s: -0.5, lo_b: -0.5})]
```

Here every factor is written as a list of (file, {column: weight}). The factor is the weighted sum of columns. `_hl` gives +0.5 to each long leg and -0.5 to each short leg. That is the same as `0.5*(A+B) - 0.5*(C+D)` from `ground_truth.py`, written another way.

```python
def _smb(f, x, w):
    cols = {"SMALL Lo" + x: w, "ME1 " + x + "2": w, "SMALL Hi" + x: w,
            "BIG Lo" + x: -w, "ME2 " + x + "2": -w, "BIG Hi" + x: -w}
    return [(f, cols)]
```

SMB: weight `+w` on the three small portfolios and `-w` on the three big ones. For `x = "BM"` the column names become `SMALL LoBM`, `ME1 BM2`, `SMALL HiBM`, and so on.

```python
RECIPES = {
    "HML": _hl(P2x3, "SMALL HiBM", "BIG HiBM", "SMALL LoBM", "BIG LoBM"),
    "SMB_3F": _smb(P2x3, "BM", 1 / 3),
    "SMB_5F": _smb(P2x3, "BM", 1 / 9) + _smb(OP, "OP", 1 / 9) + _smb(INV, "INV", 1 / 9),
```

SMB_3F uses weight 1/3 (an average of 3). SMB_5F uses 1/9 across three files (an average of 9 small minus an average of 9 big). The other tasks match `ground_truth.py` leg for leg, including Low minus High for the reversals.

### `_wrong_formula(task_id)`

```python
    if task_id == "SMB_3F":                # forgot the neutral portfolios: 2-vs-2 average
        return [(P2x3, {"SMALL LoBM": 0.5, "SMALL HiBM": 0.5, "BIG LoBM": -0.5, "BIG HiBM": -0.5})]
    if task_id == "SMB_5F":
        return RECIPES["SMB_3F"]           # used the 3-factor SMB definition
    # keep only the small-stock legs (and double them): Small Hi - Small Lo
    f, w = RECIPES[task_id][0]
    return [(f, {c: 2 * v for c, v in w.items() if c.startswith("SMALL")})]
```

A believable wrong recipe per task. For SMB_3F, it drops the neutral portfolios. For SMB_5F, it uses the 3-factor SMB (the scorer should tag this with the detail `SMB_SWAP`). For the rest, it keeps only the two small-stock columns and doubles their weights (from ±0.5 to ±1), giving just the small-stock spread.

### The script template

```python
SCRIPT = '''import pandas as pd

RECIPE = {recipe}
TABLE = "{table}"
```

`SCRIPT` is the text of a Python program with blanks (`{recipe}`, `{table}`, `{mutate}`, `{dates}`, `{outname}`) to be filled in by `.format()`. Where the fake script itself needs real curly braces (like `rows = {{}}`), they are doubled so `.format()` leaves them as single braces.

Inside the template, `read_block` finds the first line containing the table title, takes the next header line that starts with a comma, and reads 6-digit date rows until the first non-monthly line. It turns `-99.99` and `-999` into missing values. The main part then computes `sum(w * df[c] ...)` for each file and adds the files together, drops missing months, applies `{mutate}`, and writes the CSV.

### `make_response(task_id, run_key, p_ok=0.7)`

```python
    seed = int(hashlib.sha256(run_key.encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    variant = "OK" if rng.random() < p_ok else rng.choice(BROKEN)
```

Picks a variant at random, but **deterministically**: the random generator is seeded from a hash of the run key. The same run key always gets the same variant, so a rerun of the dry run is reproducible. With `p_ok=0.7`, about 70% are OK and the rest are one of the 10 broken variants, chosen evenly.

```python
    if variant == "SIGN_FLIP":
        mutate = "total = -total"
    elif variant == "UNITS":
        mutate = "total = total * 100"
    elif variant == "PARTIAL_COVERAGE":
        mutate = "total = total.iloc[len(total) // 2:]"
```

Each broken variant changes one blank in the template. `iloc[n:]` selects rows by position, from row `n` to the end. DATE_MISALIGN converts dates to pandas monthly **Periods**, adds 1 (one month later), and converts back to YYYYMM. CRASH inserts `raise RuntimeError(...)`. NO_OUTPUT changes the file name. BAD_FORMAT writes dates as text like `1926-07`. WRONG_BLOCK changes the table title to the equal-weighted one.

```python
    if variant == "NO_CODE":
        text = "I would parse the first table and compute the factor, but I cannot write the code."
    else:
        text = f"Here is the script ({variant}, dry run).\n\n```python\n{code}```\n\nIt writes output.csv."
    return variant, text
```

The reply is wrapped in a Markdown code block, like a real model reply, so the harness's `extract_code` is tested too.

## Walkthrough of `selftest.py`

### Setup

```python
import dryrun_mock
import run_experiment as rx
import score
```

It reuses the real harness (`run_experiment`, imported as `rx` for short) and the real scorer. Nothing is reimplemented, so the test checks the actual code.

```python
def fake_meta(code, task, run_dir, timeout=rx.SCRIPT_TIMEOUT_S):
    meta = dict(status="done", task=task, has_code=code is not None, stop_reason="end_turn")
    if code is not None:
        meta.update(rx.run_script(code, TASKS[task]["input_files"], RAW, run_dir, timeout))
    return meta
```

Builds the same kind of `meta` dictionary `run_experiment.py` would, by actually running the script with the real `run_script`.

```python
refs = score.build_references(doc["tasks"])
variants = ["OK"] + dryrun_mock.BROKEN
expected = {"OK": "PASS"}
```

Loads the scorer's reference series once. The expected tag for each variant is the variant's own name, except OK, which should be PASS.

### Forcing each variant

```python
            k = 0
            while True:
                got, text = dryrun_mock.make_response(task, f"selftest|{task}|{v}|{k}", p_ok=0.0 if v != "OK" else 1.0)
                if got == v:
                    break
                k += 1
```

`make_response` picks variants at random, so to get a specific one the test tries run keys `...|0`, `...|1`, ... until the mock returns the wanted variant. With `p_ok=0.0` it always picks a broken one; with `p_ok=1.0` it always picks OK.

```python
            code, _ = rx.extract_code(text)
            row = score.score_run(fake_meta(code, task, run_dir), run_dir, refs[task], doc["pass_rule"])
            want = expected.get(v, v)
            n += 1
            ok = row["primary_tag"] == want
            if v == "WRONG_FORMULA" and task == "SMB_5F":
                ok = ok and "SMB_SWAP" in row["tag_detail"]
```

Extract the code, run it, score it, and compare the scorer's primary tag with what was planted. `expected.get(v, v)` means "look up `v`, and if it is not there, use `v` itself". For the SMB_5F wrong formula it also checks the detail mentions `SMB_SWAP`.

### Timeout check

```python
    row = score.score_run(fake_meta("import time\ntime.sleep(10)\n", "HML", run_dir, timeout=2),
                          run_dir, refs["HML"], doc["pass_rule"])
```

A script that sleeps 10 seconds, run with a 2-second limit (to keep the test fast). It must be tagged TIMEOUT.

### API-key leak check

```python
    os.environ["ANTHROPIC_API_KEY"] = "sk-test-should-not-leak"
    ...
    rx.run_script("import os\nopen('output.csv','w').write(os.environ.get('ANTHROPIC_API_KEY','none'))\n",
                  [], RAW, run_dir)
    leaked = open(os.path.join(run_dir, "output.csv")).read() != "none"
```

Sets a fake key in the harness's environment, then runs a script that tries to read it and write it to a file. If the file says `none`, the key was hidden. This confirms `run_script`'s stripped environment works.

```python
print(f"\n{n - len(failures)}/{n} checks passed")
sys.exit(1 if failures else 0)
```

Exit code 1 means failure. That is useful if you ever run it automatically.

## If something goes wrong

- **A `BAD` line, for example `BAD SMB_3F UNITS -> WRONG_FORMULA`** - the scorer mislabeled a planted mistake. Do not run real experiments until it is fixed. Look at `diagnose()` in `score.py` (doc 06), and check that `data/truth/` is current by rerunning `ground_truth.py`.
- **`BAD HML OK -> CRASH`** (or every OK fails) - the scripts cannot run. Usually the venv is not active, so pandas is missing for the subprocess. Run `source .venv/bin/activate` and try again.
- **`BAD API key hidden from model script`** - someone changed the `env=` dictionary in `run_script` to pass the full environment. Restore the minimal one.
- **`FileNotFoundError` for `data/truth/HML.csv`** - run `ground_truth.py` and `make_tasks.py` first.

## Check your understanding

1. Why test the scorer with fake scripts instead of just trusting it?
2. Why does `make_response` seed its random generator from the run key?
3. What does the API-key check prove?

<details>
<summary>Answers</summary>

1. With fake scripts you know the true mistake because you planted it. If the scorer's tag matches the planted mistake every time, you can trust its tags on real model output, where you do not know the answer in advance.
2. So the same run key always gets the same variant. Dry runs are reproducible, and the self-test can search for a key that gives the variant it wants.
3. That a script run by the harness cannot read `ANTHROPIC_API_KEY`, even when it is set in the harness's own environment.

</details>
