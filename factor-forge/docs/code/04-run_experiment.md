# 04 - `run_experiment.py`

## In one sentence

`run_experiment.py` is the harness: for every model, task, condition and repeat it sends the prompt to Claude, pulls the Python code out of the reply, runs that code in a clean temporary folder with a 60-second limit, and saves everything to disk.

## Why it exists

This is where the experiment actually happens. 8 tasks x 2 conditions x 4 models x 5 repeats = 320 runs. Doing that by hand would be slow and error-prone. This script does each run the same way, records tokens, cost and timing, and is **resume-safe**: if it stops halfway (Ctrl-C, Wi-Fi drop), you rerun the same command and it skips finished runs.

It does not grade anything. Grading is `score.py`'s job. This script only collects the raw material.

## How to run it

From inside `~/letting-claude-cook/factor-forge` with the venv active.

Free test with the fake model (no API key, no cost):

```bash
python run_experiment.py --dry-run --repeats 2
```

Tiny real pilot (1 API call per condition, so 2 calls):

```bash
python run_experiment.py --models haiku --tasks HML --repeats 1
```

Full run (320 calls):

```bash
python run_experiment.py --repeats 5
```

Real output from the dry run (shortened):

```
128 runs requested, 0 already done, 128 to do -> /.../factor-forge/runs_dryrun  [DRY RUN]
[1/128] HML|RECIPE|fable|r1          done      stop=end_turn rc=0 out=True tok=1387/347 $0.0312 0.0s variant=OK
[2/128] HML|NAME_ONLY|fable|r1       done      stop=end_turn rc=0 out=True tok=1315/352 $0.0307 0.0s variant=UNITS
[3/128] SMB_3F|RECIPE|fable|r1       done      stop=end_turn rc=0 out=True tok=1398/379 $0.0329 0.0s variant=OK
...
finished 128 runs, cost this session $1.73 (fake)
```

Each progress line shows: run number, run key (task|condition|model|repeat), status, why the model stopped (`stop=`), the script's exit code (`rc=0` means it exited normally), whether it wrote `output.csv` (`out=`), input/output tokens, cost, and API latency. In a dry run the tokens and cost are made up, and `variant=` shows which planted mistake the fake model used. Real runs print the same line without `variant=`.

If you rerun the same command, finished runs are skipped:

```
128 runs requested, 128 already done, 0 to do -> /.../factor-forge/runs_dryrun  [DRY RUN]
finished 0 runs, cost this session $0.00 (fake)
```

All options:

| flag | default | meaning |
|---|---|---|
| `--models` | all four | any of `fable opus sonnet haiku` |
| `--tasks` | all eight | any task ids |
| `--conditions` | both | `RECIPE`, `NAME_ONLY` |
| `--repeats` | 5 | repeats per cell |
| `--dry-run` | off | use the fake model |
| `--out` | `runs/` or `runs_dryrun/` | output folder |
| `--effort` | `high` | same reasoning effort for every model |
| `--max-tokens` | 32000 | reply length limit |
| `--workers` | 2 | API calls in parallel |
| `--timeout` | 60 | seconds allowed for each script |
| `--api-attempts` | 3 | outer retries on API errors |
| `--limit` | none | only do the first N pending runs |

## What gets saved

Each run gets a folder `runs/<model>/<task>/<condition>/r<k>/`, for example `runs/haiku/HML/RECIPE/r1/`, holding:

- `prompt.txt` - the exact prompt
- `response.txt` - the model's reply text
- `response.json` - the full API message
- `solution.py` - the extracted code
- `stdout.txt`, `stderr.txt` - what the script printed (stderr holds error messages)
- `output.csv` - the script's output, if it wrote one
- `meta.json` - the record of the run, written last

Real `meta.json` from a dry run (shortened):

```json
{
  "run_key": "HML|RECIPE|haiku|r1",
  "model_id": "claude-haiku-5-5",
  "condition": "RECIPE",
  "dry_run": true,
  "effort": "high",
  "prompt_version": "v1",
  "prompt_sha": "af9b1d9c02cdcb31",
  "stop_reason": "end_turn",
  "input_tokens": 1387,
  "output_tokens": 347,
  "n_code_blocks": 1,
  "has_code": true,
  "cost_usd": 0.000312,
  "returncode": 0,
  "timed_out": false,
  "script_runtime_s": 0.17,
  "has_output": true,
  "status": "done",
  ...
}
```

The folder also gets `manifest.json`, a log of every time you ran the command, with its settings and library versions.

## Walkthrough

### Models and prices

```python
MODELS = {
    # alias:  (API model id,        $ in / 1M, $ out / 1M)
    "fable":  ("claude-fable-5-1",  10.00, 50.00),
    "opus":   ("claude-opus-5-5",    4.00, 20.00),
    "sonnet": ("claude-sonnet-5-5",  2.00, 10.00),
    "haiku":  ("claude-haiku-5-5",   0.10,  0.50),
}
MODEL_ORDER = ["fable", "opus", "sonnet", "haiku"]   # expected best -> worst
```

Short names, real API model ids, and prices in US dollars per million tokens (input, output). A **token** is a chunk of text, roughly 3-4 characters. The comment in the file says to re-check prices before the real run. `MODEL_ORDER` is the expected ranking, used later by `analyze.py` to decide which pairs of models to compare.

```python
SCRIPT_TIMEOUT_S = 60          # wall-clock limit for the model's script
MAX_OUTPUT_BYTES = 5_000_000   # don't copy back absurdly large output files
FATAL_API_ERRORS = ("AuthenticationError", "PermissionDeniedError", "NotFoundError", "BadRequestError")
```

`FATAL_API_ERRORS` are errors that retrying will not fix (bad key, wrong model id, bad request). The underscores in `5_000_000` are just for readability.

### `log(msg)` and the lock

```python
print_lock = threading.Lock()


def log(msg):
    with print_lock:
        print(msg, flush=True)
```

Runs happen in parallel threads (see `main`). A **lock** lets only one thread print at a time, so lines do not get mixed together. `flush=True` makes the line appear right away.

### `cost_usd(alias, input_tokens, output_tokens)`

```python
    _, p_in, p_out = MODELS[alias]
    if alias == "haiku" and input_tokens > HAIKU_LONG[0]:
        p_in, p_out = HAIKU_LONG[1], HAIKU_LONG[2]
    return input_tokens * p_in / 1e6 + output_tokens * p_out / 1e6
```

Cost = tokens x price per million / 1,000,000. Haiku has a higher price for very long prompts (over 100K tokens). These prompts are about 2-5K tokens, so that branch is not used in practice. The docstring notes that "thinking" tokens (the model's hidden reasoning) are counted in output tokens, so they are paid for.

### `call_claude(...)` - one real API call

```python
    kwargs = dict(model=model_id, max_tokens=max_tokens,
                  messages=[{"role": "user", "content": prompt}])
    if effort != "default":
        kwargs["output_config"] = {"effort": effort}   # same effort for every model = fair
```

The request is just the model id, a length limit, and one user message (the prompt). No system prompt, no tools, no temperature (the docstring says these models reject it). Effort is set the same for every model, so a difference in results cannot come from one model thinking harder by default.

`kwargs` ("keyword arguments") is a dictionary that gets unpacked into the function call with `**kwargs`.

```python
    t0 = time.time()
    with client.messages.stream(**kwargs) as stream:
        msg = stream.get_final_message()
    latency = time.time() - t0
```

It uses **streaming**: the reply arrives in pieces. The docstring explains why: with long thinking, the SDK refuses non-streaming calls that might take more than about 10 minutes. `get_final_message()` waits for the whole reply. `time.time()` before and after measures latency in seconds.

```python
    text = "".join(b.text for b in msg.content if b.type == "text")
    refusal = getattr(msg.stop_details, "category", None) if msg.stop_reason == "refusal" else None
```

A reply is a list of content blocks. Some are "thinking" blocks. Only "text" blocks are the answer, so only those are joined. If the model refused, the refusal category is recorded. `getattr(obj, "name", None)` gets an attribute, or `None` if it does not exist.

It returns a dictionary with the text, the full message (`raw`), the stop reason, token counts and latency.

### `call_fake(task_id, run_key, prompt)` - the dry-run stand-in

```python
    import dryrun_mock
    variant, text = dryrun_mock.make_response(task_id, run_key)
    return dict(text=text, raw={"dry_run": True, "variant": variant}, model_returned="dry-run",
                stop_reason="end_turn", refusal_category=None,
                input_tokens=len(prompt) // 4, output_tokens=len(text) // 4,
```

Same shape of result as `call_claude`, but the reply comes from `dryrun_mock.py` (doc 05) and no network is used. Token counts are faked as characters divided by 4 (`//` is whole-number division).

### `extract_code(text)` - pull the script out of the reply

```python
FENCE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[^\n]*\n(.*?)```", re.DOTALL)
```

A regex that finds Markdown code blocks:

- ` ``` ` - three backticks open the block.
- `[ \t]*` - optional spaces or tabs.
- `([A-Za-z0-9_+-]*)` - group 1: the language tag, like `python` (may be empty).
- `[^\n]*\n` - the rest of that line, then the newline.
- `(.*?)` - group 2: the code. `*?` is "non-greedy": match as little as possible, so it stops at the first closing ` ``` ` instead of the last one.
- `re.DOTALL` lets `.` match newlines too, so the code can span many lines.

```python
    blocks = FENCE.findall(text or "")
    py = [code for lang, code in blocks if lang.lower() in ("python", "py", "python3")]
    if not py:
        py = [code for lang, code in blocks if lang == ""]
    if not py:
        return None, 0
    return max(py, key=len), len(py)
```

`findall` returns a list of (language, code) pairs. It prefers blocks tagged `python`/`py`/`python3`. If there are none, it falls back to untagged blocks. If there are several, it takes the longest (`max(..., key=len)`). It returns the code and how many candidate blocks there were. `None` means no code was found; the scorer tags that run NO_CODE.

### `run_script(...)` - run the model's code

```python
    with tempfile.TemporaryDirectory(prefix="ff_run_") as tmp:
        for f in input_files:
            shutil.copy(os.path.join(raw_dir, f), os.path.join(tmp, f))
        with open(os.path.join(tmp, "solution.py"), "w") as fh:
            fh.write(code)
```

`tempfile.TemporaryDirectory` makes a brand-new empty folder that is deleted automatically when the `with` block ends. Only the task's input files are copied in. The official factor files are never copied, so the script cannot read the answer.

```python
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": tmp,
               "LANG": "en_US.UTF-8", "MPLBACKEND": "Agg"}
```

The script gets a minimal set of **environment variables**. Your `ANTHROPIC_API_KEY` is not in this list, so the model's code cannot see it. `selftest.py` checks this. The docstring is honest that this is not a real security sandbox: the script still runs as you, on your machine.

```python
        try:
            p = subprocess.run([sys.executable, "-I", "solution.py"], cwd=tmp, env=env,
                               capture_output=True, text=True, timeout=timeout)
            rc, out, err, timed_out = p.returncode, p.stdout, p.stderr, False
        except subprocess.TimeoutExpired as e:
            rc, timed_out = None, True
```

**subprocess** runs another program from Python. Here it runs `python -I solution.py`:

- `sys.executable` is the Python that is running this harness (your venv's Python), so the script gets the same pandas and numpy.
- `-I` is isolated mode: no `PYTHON...` environment variables, no user site-packages, and the script's own folder is not added to the import path.
- `cwd=tmp` runs it inside the temp folder, so `pd.read_csv("6_Portfolios_2x3.csv")` finds the file.
- `capture_output=True, text=True` collects what it prints as strings.
- `timeout=timeout` is the 60-second limit. If the script runs longer, Python kills it and raises `subprocess.TimeoutExpired`, which is caught by the `except` block. The run is marked `timed_out=True`.
- `returncode` 0 means the script finished normally. Anything else means it crashed.

The next lines in the `except` block decode any partial output captured before the kill (it may arrive as bytes).

```python
        out_path = os.path.join(tmp, "output.csv")
        has_output = os.path.isfile(out_path)
        if has_output and os.path.getsize(out_path) <= MAX_OUTPUT_BYTES:
            shutil.copy(out_path, os.path.join(run_dir, "output.csv"))
```

If the script wrote `output.csv` and it is not huge, it is copied into the run's folder before the temp folder is deleted. Then the last 20,000 characters of stdout and stderr are saved. It returns the exit code, whether it timed out, the run time, and whether output exists.

### `do_run(job, args, client, raw_dir)` - one complete run

```python
    run_key = f"{task}|{cond}|{alias}|r{rep}"
    run_dir = job["dir"]
    os.makedirs(run_dir, exist_ok=True)
    # remove leftovers of an earlier, unfinished attempt
    for f in ("output.csv", "solution.py", "stdout.txt", "stderr.txt"):
```

Makes the run folder and deletes leftovers from an interrupted attempt, so an old `output.csv` cannot be mistaken for a new one.

```python
    prompt = prompts.build_prompt(job["task_obj"], cond, raw_dir)
```

Builds the prompt with `prompts.py`, saves it to `prompt.txt`, and starts a `meta` dictionary with run details, effort, prompt version and prompt hash.

```python
    for attempt in range(1, args.api_attempts + 1):
        try:
            if args.dry_run:
                resp = call_fake(task, run_key, prompt)
            else:
                resp = call_claude(client, MODELS[alias][0], prompt, args.effort, args.max_tokens)
            break
        except Exception as e:  # noqa: BLE001 -- we log every failure type
            last_err = f"{type(e).__name__}: {e}"
            if type(e).__name__ in FATAL_API_ERRORS:
```

Calls the model, with up to 3 tries. `break` leaves the loop on success. If the error is fatal (bad key, wrong model), it saves `meta.json` with `status="api_error"` and stops the whole program with `SystemExit` and a message telling you to check your key or model id. For other errors (like a temporary overload) it logs, waits (`time.sleep(min(60, 10 * attempt))`: 10 seconds after the first failure, 20 after the second, 30 after the third), and tries again. (The Anthropic client also retries on its own, up to 5 times.) If all tries fail, the run is saved as `api_error` and the function returns. It is not marked done, so a rerun will try it again.

```python
    code, n_blocks = extract_code(text)
    meta.update(resp)
    meta.update(n_code_blocks=n_blocks, has_code=code is not None,
                cost_usd=round(cost_usd(alias, resp["input_tokens"], resp["output_tokens"]), 6))
```

Saves the reply, extracts the code, and adds tokens and cost to `meta`. `dict.update` adds or overwrites keys.

```python
    if code is not None:
        with open(os.path.join(run_dir, "solution.py"), "w") as fh:
            fh.write(code)
        meta.update(run_script(code, job["task_obj"]["input_files"], raw_dir, run_dir, args.timeout))
    else:
        meta.update(returncode=None, timed_out=False, script_runtime_s=None, has_output=False)

    meta.update(status="done", finished_at=dt.datetime.now().isoformat(timespec="seconds"))
    _write_json(os.path.join(run_dir, "meta.json"), meta)   # written last = run is complete
```

Runs the code if there is any. Then marks the run `done` and writes `meta.json` **last**. That ordering is what makes resuming safe: if `meta.json` says done, every other file is already there.

### `_write_json(path, obj)` - safe writing

```python
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(obj, fh, indent=2, default=str)
    os.replace(tmp, path)   # atomic: never leaves a half-written meta.json
```

Writes to a temporary file, then renames it over the real name. A rename is **atomic**: it either fully happens or does not. So if the program is killed mid-write, you never get a half-written `meta.json`. `default=str` turns anything JSON cannot store directly into text.

### `is_complete(run_dir, dry_run)`

```python
    if m.get("dry_run") != dry_run:
        raise SystemExit(f"{run_dir} holds a {'dry' if m.get('dry_run') else 'real'} run; "
                         "use a different --out folder so dry and real runs never mix.")
    return m.get("status") == "done"
```

A run is complete if its `meta.json` exists and says `done`. It also refuses to mix fake and real runs in the same folder, so fake results can never end up in the real data.

### `write_manifest(out, args, jobs)`

Appends one entry to `<out>/manifest.json` each time you run the command: time, the exact command line (`sys.argv`), effort, max tokens, timeout, models and prices, number of jobs, prompt version, and the versions of Python, the Anthropic SDK, pandas and numpy. This is a reproducibility record. The `try/except ImportError` allows a dry run without the `anthropic` package installed.

### `main()`

```python
    ap.add_argument("--models", nargs="+", default=MODEL_ORDER, choices=list(MODELS))
```

`nargs="+"` means the flag takes one or more values (`--models haiku sonnet`). `choices=` rejects anything not in the list with a clear error.

```python
    for f in doc["never_give_model"]:          # sanity check: answers never reach the model
        assert all(f not in t["input_files"] for t in tasks.values()), f
```

Before anything runs, it checks that no official answer file is in any task's inputs.

```python
    if not args.dry_run:
        import anthropic
        from dotenv import load_dotenv
        load_dotenv(os.path.join(HERE, ".env"))
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")
        # No server-side model fallbacks: every answer must come from the named model.
        client = anthropic.Anthropic(max_retries=5, timeout=900)
```

For real runs only: load your key from `.env` (via `python-dotenv`), stop with a clear message if it is missing, and create the API client with up to 5 automatic retries and a 900-second (15-minute) timeout per call.

```python
    for rep in range(1, args.repeats + 1):
        for alias in args.models:
            for t in args.tasks:
                for c in args.conditions:
```

Builds the full job list. The repeat is the outermost loop ("repeat-major order"). So all of repeat 1 for every model and task comes before any of repeat 2. If you stop partway, you still have a balanced sample across models.

```python
    pending = [j for j in jobs if not is_complete(j["dir"], args.dry_run)]
    n_already = len(jobs) - len(pending)
    if args.limit:
        pending = pending[:args.limit]
```

Drops finished runs. `--limit N` keeps only the first N pending ones, useful for a pilot.

```python
    with cf.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futs = {pool.submit(do_run, j, args, client, raw_dir): j for j in pending}
        for fut in cf.as_completed(futs):
            m = fut.result()
```

A **thread pool** runs several `do_run` calls at once (2 by default). This is useful because most of the time is spent waiting for the API. `pool.submit` starts a job and returns a "future" (a placeholder for a result that is not ready yet). `as_completed` hands back futures in the order they finish, and `fut.result()` gets the `meta` dictionary. Each finished run prints one progress line and adds to the session cost.

## If something goes wrong

- **`ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.`** - do exactly that (see doc 08). Not needed for `--dry-run`.
- **`FATAL API error on HML|RECIPE|fable|r1: AuthenticationError ...`** (or `NotFoundError`) - the key is wrong or expired, or a model id in `MODELS` is not available to your account. Fix it and rerun the same command. Finished runs are kept.
- **`... holds a dry run; use a different --out folder so dry and real runs never mix.`** - you pointed a real run at a dry-run folder (or the reverse). Use the default folders or a new `--out`.
- **Lots of `! ... attempt 1 failed: ...` lines** - temporary API trouble (rate limits, overload). Lower `--workers` to 1, wait, and rerun. Runs that ended as `api_error` are retried automatically.

## Check your understanding

1. Why is `meta.json` written last?
2. How does the harness stop a model's script from reading the official answer or your API key?
3. What happens if a model's script runs for 2 minutes?

<details>
<summary>Answers</summary>

1. Because "meta.json says done" is how the script knows a run is finished. Writing it last (and atomically) means a done run always has all its other files, so resuming is safe.
2. The script runs in a new temp folder that holds only the task's input files. The official files are never copied in. It gets a minimal environment with no API key. (It is not a full security sandbox; it still runs as you.)
3. `subprocess.run` hits its 60-second `timeout`, kills the script and raises `TimeoutExpired`. The run is saved with `timed_out=True`, and `score.py` tags it TIMEOUT.

</details>
