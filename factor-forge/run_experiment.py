"""
Factor Forge -- experiment runner.

For every (model, task, condition, repeat):
  1. build the prompt (prompts.py)
  2. ask the model (Anthropic API), or a fake model with --dry-run
  3. pull the ONE python code block out of the reply
  4. run it in a fresh temp folder that holds ONLY the raw input files (60 s limit)
  5. save everything to <out>/<model>/<task>/<condition>/r<k>/

Files saved per run:
  prompt.txt, response.txt (reply text), response.json (full API message),
  solution.py (extracted code), stdout.txt, stderr.txt, output.csv (if written),
  meta.json (written LAST: model, tokens, cost, latency, return code, ...)

Resume-safe: a run whose meta.json says status "done" is skipped, so you can
stop with Ctrl-C and rerun the same command. Runs that hit an API error are retried.

Examples:
  python run_experiment.py --dry-run --repeats 2            # free test, no API key needed
  python run_experiment.py --models haiku --tasks HML --repeats 1   # tiny real pilot
  python run_experiment.py --repeats 5                      # full run (320 calls)
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

import prompts

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Models and prices (USD per 1M tokens). Source: claude-api skill model table,
# cached 2026-10-06 -- re-check https://platform.claude.com pricing before the run.
# ---------------------------------------------------------------------------
MODELS = {
    # alias:  (API model id,        $ in / 1M, $ out / 1M)
    "fable":  ("claude-fable-5-1",  10.00, 50.00),
    "opus":   ("claude-opus-5-5",    4.00, 20.00),
    "sonnet": ("claude-sonnet-5-5",  2.00, 10.00),
    "haiku":  ("claude-haiku-5-5",   0.10,  0.50),
}
MODEL_ORDER = ["fable", "opus", "sonnet", "haiku"]   # expected best -> worst
# Haiku 5.5 charges more for prompts over 100K tokens (ours are ~2-5K, so unused)
HAIKU_LONG = (100_000, 0.50, 2.50)

SCRIPT_TIMEOUT_S = 60          # wall-clock limit for the model's script
MAX_OUTPUT_BYTES = 5_000_000   # don't copy back absurdly large output files
FATAL_API_ERRORS = ("AuthenticationError", "PermissionDeniedError", "NotFoundError", "BadRequestError")

print_lock = threading.Lock()


def log(msg):
    with print_lock:
        print(msg, flush=True)


def cost_usd(alias, input_tokens, output_tokens):
    """Dollar cost of one call from token counts (thinking tokens are in output_tokens)."""
    _, p_in, p_out = MODELS[alias]
    if alias == "haiku" and input_tokens > HAIKU_LONG[0]:
        p_in, p_out = HAIKU_LONG[1], HAIKU_LONG[2]
    return input_tokens * p_in / 1e6 + output_tokens * p_out / 1e6


# ---------------------------------------------------------------------------
# Talking to the model
# ---------------------------------------------------------------------------
def call_claude(client, model_id, prompt, effort, max_tokens):
    """One fresh API call: no system prompt, no tools, no temperature (models reject it).

    Uses streaming because thinking can make big-model replies long; the SDK refuses
    non-streaming calls whose max_tokens could take more than ~10 minutes.
    """
    kwargs = dict(model=model_id, max_tokens=max_tokens,
                  messages=[{"role": "user", "content": prompt}])
    if effort != "default":
        kwargs["output_config"] = {"effort": effort}   # same effort for every model = fair
    t0 = time.time()
    with client.messages.stream(**kwargs) as stream:
        msg = stream.get_final_message()
    latency = time.time() - t0
    # The reply may start with 'thinking' blocks; only 'text' blocks are the answer.
    text = "".join(b.text for b in msg.content if b.type == "text")
    refusal = getattr(msg.stop_details, "category", None) if msg.stop_reason == "refusal" else None
    return dict(
        text=text,
        raw=msg.model_dump(mode="json"),
        model_returned=msg.model,
        stop_reason=msg.stop_reason,
        refusal_category=refusal,
        input_tokens=msg.usage.input_tokens,
        output_tokens=msg.usage.output_tokens,
        cache_read_input_tokens=msg.usage.cache_read_input_tokens or 0,
        latency_s=round(latency, 2),
    )


def call_fake(task_id, run_key, prompt):
    """Dry-run stand-in for call_claude: no network, made-up token counts."""
    import dryrun_mock
    variant, text = dryrun_mock.make_response(task_id, run_key)
    return dict(text=text, raw={"dry_run": True, "variant": variant}, model_returned="dry-run",
                stop_reason="end_turn", refusal_category=None,
                input_tokens=len(prompt) // 4, output_tokens=len(text) // 4,
                cache_read_input_tokens=0, latency_s=0.0, dry_run_variant=variant)


# ---------------------------------------------------------------------------
# Getting the code out of the reply
# ---------------------------------------------------------------------------
FENCE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[^\n]*\n(.*?)```", re.DOTALL)


def extract_code(text):
    """Return (code or None, number of python blocks found).

    Prefers ```python blocks; if there are several, takes the longest one.
    Falls back to an untagged ``` block if no python-tagged block exists.
    """
    blocks = FENCE.findall(text or "")
    py = [code for lang, code in blocks if lang.lower() in ("python", "py", "python3")]
    if not py:
        py = [code for lang, code in blocks if lang == ""]
    if not py:
        return None, 0
    return max(py, key=len), len(py)


# ---------------------------------------------------------------------------
# Running the model's script
# ---------------------------------------------------------------------------
def run_script(code, input_files, raw_dir, run_dir, timeout=SCRIPT_TIMEOUT_S):
    """Run solution.py in a brand-new temp folder containing only the input files.

    Not a security sandbox: the script runs as you. It gets a stripped-down
    environment (no API keys) and cannot see the official factor files, which
    are never copied in.
    """
    with tempfile.TemporaryDirectory(prefix="ff_run_") as tmp:
        for f in input_files:
            shutil.copy(os.path.join(raw_dir, f), os.path.join(tmp, f))
        with open(os.path.join(tmp, "solution.py"), "w") as fh:
            fh.write(code)
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": tmp,
               "LANG": "en_US.UTF-8", "MPLBACKEND": "Agg"}
        t0 = time.time()
        try:
            p = subprocess.run([sys.executable, "-I", "solution.py"], cwd=tmp, env=env,
                               capture_output=True, text=True, timeout=timeout)
            rc, out, err, timed_out = p.returncode, p.stdout, p.stderr, False
        except subprocess.TimeoutExpired as e:
            rc, timed_out = None, True
            out = (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            err = (e.stderr or b"").decode("utf-8", "replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        runtime = time.time() - t0
        out_path = os.path.join(tmp, "output.csv")
        has_output = os.path.isfile(out_path)
        if has_output and os.path.getsize(out_path) <= MAX_OUTPUT_BYTES:
            shutil.copy(out_path, os.path.join(run_dir, "output.csv"))
        elif has_output:
            has_output = False
            err += "\n[harness] output.csv too large, not copied"
    with open(os.path.join(run_dir, "stdout.txt"), "w") as fh:
        fh.write(out[-20000:])
    with open(os.path.join(run_dir, "stderr.txt"), "w") as fh:
        fh.write(err[-20000:])
    return dict(returncode=rc, timed_out=timed_out, script_runtime_s=round(runtime, 2),
                has_output=has_output)


# ---------------------------------------------------------------------------
# One run
# ---------------------------------------------------------------------------
def do_run(job, args, client, raw_dir):
    alias, task, cond, rep = job["alias"], job["task"], job["condition"], job["repeat"]
    run_key = f"{task}|{cond}|{alias}|r{rep}"
    run_dir = job["dir"]
    os.makedirs(run_dir, exist_ok=True)
    # remove leftovers of an earlier, unfinished attempt
    for f in ("output.csv", "solution.py", "stdout.txt", "stderr.txt"):
        if os.path.exists(os.path.join(run_dir, f)):
            os.remove(os.path.join(run_dir, f))

    prompt = prompts.build_prompt(job["task_obj"], cond, raw_dir)
    with open(os.path.join(run_dir, "prompt.txt"), "w") as fh:
        fh.write(prompt)

    meta = dict(run_key=run_key, model_alias=alias, model_id=MODELS[alias][0], task=task,
                condition=cond, repeat=rep, dry_run=args.dry_run, effort=args.effort,
                max_tokens=args.max_tokens, prompt_version=prompts.PROMPT_VERSION,
                prompt_sha=prompts.prompt_hash(prompt),
                started_at=dt.datetime.now().isoformat(timespec="seconds"))

    # --- 1. ask the model (with a few outer retries on top of the SDK's own) ---
    resp, last_err = None, None
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
                meta.update(status="api_error", error=last_err)
                _write_json(os.path.join(run_dir, "meta.json"), meta)
                raise SystemExit(f"FATAL API error on {run_key}: {last_err}\n"
                                 "Check your API key / model id / parameters before rerunning.")
            log(f"  ! {run_key} attempt {attempt} failed: {last_err[:200]}")
            time.sleep(min(60, 10 * attempt))
    if resp is None:
        meta.update(status="api_error", error=last_err)
        _write_json(os.path.join(run_dir, "meta.json"), meta)
        return meta

    with open(os.path.join(run_dir, "response.txt"), "w") as fh:
        fh.write(resp["text"])
    _write_json(os.path.join(run_dir, "response.json"), resp.pop("raw"))
    text = resp.pop("text")

    # --- 2. extract the code ---
    code, n_blocks = extract_code(text)
    meta.update(resp)
    meta.update(n_code_blocks=n_blocks, has_code=code is not None,
                cost_usd=round(cost_usd(alias, resp["input_tokens"], resp["output_tokens"]), 6))

    # --- 3. run it ---
    if code is not None:
        with open(os.path.join(run_dir, "solution.py"), "w") as fh:
            fh.write(code)
        meta.update(run_script(code, job["task_obj"]["input_files"], raw_dir, run_dir, args.timeout))
    else:
        meta.update(returncode=None, timed_out=False, script_runtime_s=None, has_output=False)

    meta.update(status="done", finished_at=dt.datetime.now().isoformat(timespec="seconds"))
    _write_json(os.path.join(run_dir, "meta.json"), meta)   # written last = run is complete
    return meta


def _write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(obj, fh, indent=2, default=str)
    os.replace(tmp, path)   # atomic: never leaves a half-written meta.json


def is_complete(run_dir, dry_run):
    path = os.path.join(run_dir, "meta.json")
    if not os.path.exists(path):
        return False
    with open(path) as fh:
        m = json.load(fh)
    if m.get("dry_run") != dry_run:
        raise SystemExit(f"{run_dir} holds a {'dry' if m.get('dry_run') else 'real'} run; "
                         "use a different --out folder so dry and real runs never mix.")
    return m.get("status") == "done"


def write_manifest(out, args, jobs):
    """Append this invocation's settings to <out>/manifest.json (reproducibility record)."""
    try:
        import anthropic
        sdk = anthropic.__version__
    except ImportError:
        sdk = None
    import numpy
    import pandas
    entry = dict(time=dt.datetime.now().isoformat(timespec="seconds"), argv=sys.argv,
                 dry_run=args.dry_run, effort=args.effort, max_tokens=args.max_tokens,
                 script_timeout_s=args.timeout, models={a: MODELS[a] for a in args.models},
                 n_jobs=len(jobs), prompt_version=prompts.PROMPT_VERSION,
                 anthropic_sdk=sdk, python=sys.version.split()[0],
                 pandas=pandas.__version__, numpy=numpy.__version__)
    path = os.path.join(out, "manifest.json")
    hist = json.load(open(path)) if os.path.exists(path) else []
    hist.append(entry)
    _write_json(path, hist)


def main():
    doc, tasks = prompts.load_tasks()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", default=MODEL_ORDER, choices=list(MODELS))
    ap.add_argument("--tasks", nargs="+", default=list(tasks), choices=list(tasks))
    ap.add_argument("--conditions", nargs="+", default=prompts.CONDITIONS, choices=prompts.CONDITIONS)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true", help="use the fake model (no API key, no cost)")
    ap.add_argument("--out", default=None, help="output folder (default runs/ or runs_dryrun/)")
    ap.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max", "default"],
                    help="same effort for every model (default: high)")
    ap.add_argument("--max-tokens", type=int, default=32000)
    ap.add_argument("--workers", type=int, default=2, help="parallel API calls (keep small: 1-4)")
    ap.add_argument("--timeout", type=int, default=SCRIPT_TIMEOUT_S, help="seconds allowed for each script")
    ap.add_argument("--api-attempts", type=int, default=3)
    ap.add_argument("--limit", type=int, default=None, help="only do the first N pending runs (pilot)")
    args = ap.parse_args()

    out = args.out or os.path.join(HERE, "runs_dryrun" if args.dry_run else "runs")
    raw_dir = os.path.join(HERE, "data", "raw")
    for f in doc["never_give_model"]:          # sanity check: answers never reach the model
        assert all(f not in t["input_files"] for t in tasks.values()), f

    client = None
    if not args.dry_run:
        import anthropic
        from dotenv import load_dotenv
        load_dotenv(os.path.join(HERE, ".env"))
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")
        # No server-side model fallbacks: every answer must come from the named model.
        client = anthropic.Anthropic(max_retries=5, timeout=900)

    # Build the job list (repeat-major order so a partial run is still balanced)
    jobs = []
    for rep in range(1, args.repeats + 1):
        for alias in args.models:
            for t in args.tasks:
                for c in args.conditions:
                    d = os.path.join(out, alias, t, c, f"r{rep}")
                    jobs.append(dict(alias=alias, task=t, condition=c, repeat=rep, dir=d, task_obj=tasks[t]))
    os.makedirs(out, exist_ok=True)
    pending = [j for j in jobs if not is_complete(j["dir"], args.dry_run)]
    n_already = len(jobs) - len(pending)
    if args.limit:
        pending = pending[:args.limit]
    log(f"{len(jobs)} runs requested, {n_already} already done, {len(pending)} to do -> {out}"
        + ("  [DRY RUN]" if args.dry_run else ""))
    write_manifest(out, args, pending)

    total_cost, n_done = 0.0, 0
    with cf.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futs = {pool.submit(do_run, j, args, client, raw_dir): j for j in pending}
        for fut in cf.as_completed(futs):
            m = fut.result()
            n_done += 1
            total_cost += m.get("cost_usd", 0) or 0
            log(f"[{n_done}/{len(pending)}] {m['run_key']:<28} {m['status']:<9} "
                f"stop={m.get('stop_reason')} rc={m.get('returncode')} out={m.get('has_output')} "
                f"tok={m.get('input_tokens')}/{m.get('output_tokens')} ${m.get('cost_usd', 0):.4f} "
                f"{m.get('latency_s')}s" + (f" variant={m['dry_run_variant']}" if 'dry_run_variant' in m else ""))
    log(f"finished {n_done} runs, cost this session ${total_cost:.2f}" + (" (fake)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
