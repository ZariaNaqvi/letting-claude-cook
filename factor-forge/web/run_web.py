"""
Form Forge -- experiment runner (the agent loop).

For every (task, condition, model, repeat), in REPEAT-MAJOR order:
  1. build the prompt (prompts_web.py) and open a FRESH headless browser (browser_tools.py)
  2. loop: ask the model (Anthropic Messages API, tool use) -> run its tool calls in the
     browser -> send back the observations, until it calls submit_answer, gives up,
     stops calling tools, or hits the step / time limit
  3. save everything to <out>/<task>__<cond>__<model>__r<k>/

Files saved per run:
  prompt.txt, steps.jsonl (one line per tool call), pages/step_<n>.txt (exact observation
  text the model saw), transcript.json (all messages; thinking text is never returned by
  these models, so only the block type is kept), final.json (written LAST: answer, stop
  reason, tokens, cost, wall time, blocked_attempts, visited_search_form, versions,
  User-Agent as sha256 only)

Resume-safe: a run folder with final.json is skipped (except harness errors, which are
redone), so Ctrl-C and rerunning the same command loses at most one run.

Cost control: --budget-usd stops BEFORE a run whose worst case (step cap reached) could
push the total of all finished runs in --out past the budget.

Examples:
  python web/run_web.py --dry-run --tasks T1 T4                      # fake model, live site, $0
  python web/run_web.py --dry-run --offline --tasks T1 T4            # fake model, saved pages, no network
  python web/run_web.py --pilot --models haiku sonnet --repeats 1    # real pilot
  python web/run_web.py --repeats 3 --budget-usd 100                 # main run (192 runs)
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, PROJECT)

import browser_tools as bt  # noqa: E402
import prompts_web  # noqa: E402
import sec_policy  # noqa: E402
from run_experiment import MODEL_ORDER, MODELS  # noqa: E402  (Part 2's table, read only)

HARNESS_VERSION = "web-h3"
SPEND_LEDGER = "spend.jsonl"            # one line per real API response, append-only
FIXTURES = os.path.join(HERE, "fixtures")
KEY_JSON = os.path.join(HERE, "answer_key.json")

# Cache prices relative to the base input price (claude-api skill, cached 2026-10-06):
# writes 1.25x (5-minute TTL); reads 0.025x Fable 5.1, 0.05x Opus 5.5, 0.10x Sonnet/Haiku.
CACHE_WRITE_MULT = 1.25
CACHE_READ_MULT = {"fable": 0.025, "opus": 0.05, "sonnet": 0.10, "haiku": 0.10}
HAIKU_LONG = (100_000, 0.50, 2.50)     # Haiku 5.5 price step for prompts over 100K tokens

TIME_LIMIT_S = 12 * 60
STALL_S = 120                           # a tool call slower than this is a site/harness stall:
                                        # logged, and NOT counted toward the model's time limit
MAX_NUDGES = 2                          # "please call a tool" nudges after a max_tokens stop
FATAL_API_ERRORS = ("AuthenticationError", "PermissionDeniedError", "NotFoundError", "BadRequestError")


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------
def turn_cost(alias, u):
    """$ for one API response, from its usage (input_tokens excludes cached tokens)."""
    price_alias = alias if alias in MODELS else "haiku"          # dry run: priced as Haiku, marked fake
    _, p_in, p_out = MODELS[price_alias]
    prompt = u["input_tokens"] + u["cache_creation_input_tokens"] + u["cache_read_input_tokens"]
    if price_alias == "haiku" and prompt > HAIKU_LONG[0]:
        p_in, p_out = HAIKU_LONG[1], HAIKU_LONG[2]
    return (u["input_tokens"] * p_in + u["cache_creation_input_tokens"] * p_in * CACHE_WRITE_MULT
            + u["cache_read_input_tokens"] * p_in * CACHE_READ_MULT[price_alias]
            + u["output_tokens"] * p_out) / 1e6


def worst_case_cost(alias, steps, prefix=3000, per_step_in=bt.MAX_OBS_CHARS // 4 + 300, per_step_out=2000):
    """Cost if the model uses every step, with caching: every observation at the size cap (+ the
    tool call) and ~2K output tokens a turn (thinking at --effort high). Not a hard bound -- a turn
    may use up to --max-tokens -- so do_run also stops a run once the budget is actually reached."""
    total = 0.0
    for i in range(steps):
        ctx = prefix + per_step_in * i
        total += turn_cost(alias, dict(input_tokens=0, cache_creation_input_tokens=per_step_in if i else prefix,
                                       cache_read_input_tokens=ctx - (per_step_in if i else prefix) if i else 0,
                                       output_tokens=per_step_out))
    return total


# ---------------------------------------------------------------------------
# Talking to the real model
# ---------------------------------------------------------------------------
class ClaudeCaller:
    """One run's API caller. Same system prompt, tools, effort and max_tokens for every model."""

    def __init__(self, client, model_id, tools, effort, max_tokens):
        self.client, self.model_id, self.effort, self.max_tokens = client, model_id, effort, max_tokens
        self.tools = [dict(t) for t in tools]
        # The cache prefix runs tools -> system -> messages, so the breakpoint goes on the system
        # block (the end of the fixed part) to cache tools AND system prompt together.
        self.system = [{"type": "text", "text": prompts_web.SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]

    def respond(self, messages):
        kwargs = dict(model=self.model_id, max_tokens=self.max_tokens, system=self.system, tools=self.tools,
                      messages=messages,
                      cache_control={"type": "ephemeral"})             # incremental cache on the newest turn
        if self.effort != "default":
            kwargs["output_config"] = {"effort": self.effort}
        # No temperature (rejected), no forced tool_choice (rejected on these models), no thinking
        # parameter (adaptive thinking is the default on all four), no server-side fallbacks:
        # every answer must come from the named model.
        with self.client.messages.stream(**kwargs) as stream:
            msg = stream.get_final_message()
        u = msg.usage
        usage = dict(input_tokens=u.input_tokens, output_tokens=u.output_tokens,
                     cache_creation_input_tokens=u.cache_creation_input_tokens or 0,
                     cache_read_input_tokens=u.cache_read_input_tokens or 0)
        refusal = getattr(msg.stop_details, "category", None) if msg.stop_reason == "refusal" else None
        return dict(content=msg.content, stop_reason=msg.stop_reason, usage=usage, model_returned=msg.model,
                    refusal_category=refusal)


def block_dict(b):
    """Content block -> plain dict (for tool dispatch and the saved transcript)."""
    if isinstance(b, dict):
        return b
    return b.model_dump(mode="json", exclude_none=True)


def transcript_copy(messages):
    out = []
    for m in messages:
        c = m["content"]
        if isinstance(c, str):
            out.append(dict(role=m["role"], content=c))
            continue
        blocks = []
        for b in c:
            d = dict(block_dict(b))
            if d.get("type") in ("thinking", "redacted_thinking"):
                d = {"type": d["type"], "chars": len(d.get("thinking", "") or "")}
            blocks.append(d)
        out.append(dict(role=m["role"], content=blocks))
    return out


# ---------------------------------------------------------------------------
# One run
# ---------------------------------------------------------------------------
def run_dir_for(out, job):
    return os.path.join(out, f"{job['task']}__{job['condition']}__{job['model']}__r{job['repeat']}")


def do_run(job, args, client, doc, tasks, key, ua, spent_before=0.0):
    task = tasks[job["task"]]
    alias, cond = job["model"], job["condition"]
    rd = run_dir_for(args.out, job)
    os.makedirs(os.path.join(rd, "pages"), exist_ok=True)
    for f in ("steps.jsonl", "transcript.json"):
        if os.path.exists(os.path.join(rd, f)):
            os.remove(os.path.join(rd, f))
    prompt = prompts_web.build_prompt(task, cond, doc)
    with open(os.path.join(rd, "prompt.txt"), "w") as fh:
        fh.write(prompt)
    tools = bt.TOOL_SCHEMAS + [bt.submit_tool(prompts_web.answer_schema(doc, task))]
    max_steps = args.max_steps or task["max_steps"]

    final = dict(run_key=f"{job['task']}|{cond}|{alias}|r{job['repeat']}", task=job["task"], condition=cond,
                 model_alias=alias, model_id=MODELS[alias][0] if alias in MODELS else f"mock:{job['persona']}",
                 repeat=job["repeat"], dry_run=args.dry_run, persona=job.get("persona"), effort=args.effort,
                 max_tokens=args.max_tokens, max_steps=max_steps, time_limit_s=args.time_limit,
                 fetch_mode="offline" if args.offline else "live", pilot=args.pilot,
                 prompt_version=prompts_web.PROMPT_VERSION, harness_version=HARNESS_VERSION,
                 prompt_sha=prompts_web.prompt_hash(prompts_web.SYSTEM_PROMPT, prompt, json.dumps(tools)),
                 user_agent_sha256=sec_policy.ua_digest(ua),
                 started_at=dt.datetime.now().isoformat(timespec="seconds"))

    if args.dry_run:
        import mock_agent
        caller = mock_agent.MockModel(job["persona"], task, key["tasks"][job["task"]])
    else:
        caller = ClaudeCaller(client, MODELS[alias][0], tools, args.effort, args.max_tokens)

    browser, steps_fh = None, None
    messages = [{"role": "user", "content": prompt}]
    tot = dict(input_tokens=0, output_tokens=0, cache_creation_input_tokens=0, cache_read_input_tokens=0)
    cost, steps, turns, nudges, stall_s, n_stalls = 0.0, 0, 0, 0, 0.0, 0
    answer, stop, error, last_stop_reason = None, None, None, None
    t0 = time.time()
    try:
        browser = bt.BrowserSession(ua, mode="offline" if args.offline else "live",
                                    fixtures=FIXTURES if args.offline else None)
        steps_fh = open(os.path.join(rd, "steps.jsonl"), "w")
        while stop is None:
            if time.time() - t0 - stall_s > args.time_limit:
                stop = "time_limit"
                break
            if not args.dry_run and spent_before + cost >= args.budget_usd:
                stop, error = "harness_error", "budget reached mid-run"     # redone on the next resume
                break
            resp = _call_with_retries(caller, messages, args)
            turns += 1
            for k in tot:
                tot[k] += resp["usage"][k]
            cost += turn_cost(alias, resp["usage"])
            if not args.dry_run:
                log_spend(args.out, final["run_key"], turn_cost(alias, resp["usage"]))
            last_stop_reason = resp["stop_reason"]
            if resp.get("refusal_category"):
                final["refusal_category"] = resp["refusal_category"]
            messages.append({"role": "assistant", "content": resp["content"]})
            uses = [block_dict(b) for b in resp["content"] if block_dict(b).get("type") == "tool_use"]
            if not uses:
                if resp["stop_reason"] == "max_tokens" and nudges < MAX_NUDGES:
                    nudges += 1
                    messages.append({"role": "user", "content": "Your turn hit the output limit. Continue by "
                                                                "calling one tool."})
                    continue
                stop = "refusal" if resp["stop_reason"] == "refusal" else "no_tool_call"
                break
            results = []
            for tu in uses:
                if steps >= max_steps:
                    stop = "step_limit"
                    break
                steps += 1
                name, inp = tu["name"], tu.get("input") or {}
                url_before = browser.page.url
                ts = time.time()
                n_blocked = browser.blocked_attempts
                if name == "submit_answer":
                    answer = inp
                    stop = "gave_up" if inp.get("give_up") else "answered"
                    obs = "Answer received. The task is over."
                else:
                    obs = browser.run_tool(name, inp)
                if time.time() - ts > STALL_S:
                    stall_s += time.time() - ts
                    n_stalls += 1
                with open(os.path.join(rd, "pages", f"step_{steps:02d}.txt"), "w") as fh:
                    fh.write(obs)
                steps_fh.write(json.dumps(dict(
                    step=steps, turn=turns, tool=name, args=inp, url_before=url_before, url_after=browser.page.url,
                    http_status=browser.last_status, blocked=browser.blocked_attempts > n_blocked,
                    error=obs.startswith("ERROR"), obs_chars=len(obs), obs_tokens_est=len(obs) // 4,
                    obs_sha256=hashlib.sha256(obs.encode()).hexdigest()[:16],
                    latency_s=round(time.time() - ts, 2), **resp["usage"])) + "\n")
                steps_fh.flush()
                results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": obs})
                if stop:
                    break
            messages.append({"role": "user", "content": results} if results else
                            {"role": "user", "content": "(no tool results)"})
            if browser.site_errors >= 3:
                stop, error = "harness_error", "site_error on 3 page loads"
            if browser.policy.http_403:
                stop, error = "harness_error", "SEC answered 403 (undeclared automated tool) -- back off"
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 -- anything else is a harness problem, rerun later
        stop, error = "harness_error", f"{type(e).__name__}: {str(e)[:300]}"
    finally:
        if steps_fh is not None:
            steps_fh.close()
        if browser is not None:
            visited = list(browser.visited)
            pages_seen = len(browser.pages_seen)
            pol = browser.policy
            blocked, n_net, misses, n403 = browser.blocked_attempts, pol.n_network, len(pol.offline_misses), pol.http_403
            api403 = pol.api_403
            site_errors = browser.site_errors
            with open(os.path.join(rd, "requests.jsonl"), "w") as fh:     # every request and the policy decision
                for t_, u_, rt_, dec_ in pol.log:
                    fh.write(json.dumps(dict(t=t_, url=u_, type=rt_, decision=dec_)) + "\n")
            browser.close()
        else:
            visited, pages_seen, blocked, n_net, misses, n403, site_errors = [], 0, 0, 0, 0, 0, 0
            api403 = 0

    with open(os.path.join(rd, "transcript.json"), "w") as fh:
        json.dump(transcript_copy(messages), fh, indent=1, default=str)
    final.update(stop_reason=stop, last_api_stop_reason=last_stop_reason, error=error, answer=answer,
                 steps=steps, turns=turns, nudges=nudges, **tot, cost_usd=round(cost, 6), cost_is_fake=args.dry_run,
                 wall_s=round(time.time() - t0, 1), stall_s=round(stall_s, 1), n_stalls=n_stalls,
                 blocked_attempts=blocked,
                 visited_search_form=any("/search-filings" in u or "/edgar/searchedgar" in u for u in visited),
                 visited_urls=visited, n_observations=pages_seen, network_requests=n_net,
                 offline_misses=misses, http_403=n403, api_403=api403, site_errors=site_errors,
                 finished_at=dt.datetime.now().isoformat(timespec="seconds"))
    tmp = os.path.join(rd, "final.json.tmp")
    with open(tmp, "w") as fh:
        json.dump(final, fh, indent=2, default=str)
    os.replace(tmp, os.path.join(rd, "final.json"))      # written last = run complete
    return final


def _call_with_retries(caller, messages, args):
    last = None
    for attempt in range(1, args.api_attempts + 1):
        try:
            return caller.respond(messages)
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            if type(e).__name__ in FATAL_API_ERRORS:
                raise SystemExit(f"FATAL API error: {last}\nCheck the API key / model id / parameters.")
            log(f"  ! API attempt {attempt} failed: {last[:200]}")
            time.sleep(min(60, 10 * attempt))
    raise RuntimeError(f"API failed {args.api_attempts} times: {last}")


# ---------------------------------------------------------------------------
# Jobs, resume, budget
# ---------------------------------------------------------------------------
def read_final(rd):
    p = os.path.join(rd, "final.json")
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        return json.load(fh)


def log_spend(out, run_key, usd):
    """Append one API response's cost to <out>/spend.jsonl. Unlike final.json, this ledger is
    never overwritten, so redone harness_error runs and interrupted runs still count."""
    with open(os.path.join(out, SPEND_LEDGER), "a") as fh:
        fh.write(json.dumps(dict(t=round(time.time(), 1), run_key=run_key, usd=round(usd, 6))) + "\n")


def spent_usd(out):
    """Real money spent in this --out folder: the spend ledger, or for folders made before the
    ledger existed (harness web-h1), the sum of the finished runs' cost_usd."""
    ledger = os.path.join(out, SPEND_LEDGER)
    if os.path.exists(ledger):
        with open(ledger) as fh:
            return sum(json.loads(ln)["usd"] for ln in fh if ln.strip())
    total = 0.0
    if not os.path.isdir(out):
        return 0.0
    for d in os.listdir(out):
        f = read_final(os.path.join(out, d))
        if f and not f.get("cost_is_fake"):
            total += f.get("cost_usd") or 0
    return total


def write_manifest(out, args, n_jobs):
    import anthropic
    from importlib.metadata import version as pkg_version
    entry = dict(time=dt.datetime.now().isoformat(timespec="seconds"), argv=sys.argv, dry_run=args.dry_run,
                 offline=args.offline, pilot=args.pilot, effort=args.effort, max_tokens=args.max_tokens,
                 time_limit_s=args.time_limit, budget_usd=args.budget_usd,
                 models={a: MODELS[a] for a in args.models}, cache_read_mult=CACHE_READ_MULT,
                 n_jobs=n_jobs, prompt_version=prompts_web.PROMPT_VERSION, harness_version=HARNESS_VERSION,
                 anthropic_sdk=anthropic.__version__, playwright=pkg_version("playwright"),
                 python=sys.version.split()[0], max_rps=sec_policy.MAX_RPS)
    path = os.path.join(out, "manifest.json")
    hist = json.load(open(path)) if os.path.exists(path) else []
    hist.append(entry)
    with open(path, "w") as fh:
        json.dump(hist, fh, indent=2)


def _list(vals):
    """Accept both --tasks T1 T4 and --tasks T1,T4 (and 'all')."""
    out = []
    for v in vals or []:
        out += [x for x in v.split(",") if x]
    return out


def main():
    doc, tasks = prompts_web.load_tasks()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", default=MODEL_ORDER)
    ap.add_argument("--tasks", nargs="+", default=["all"])
    ap.add_argument("--conditions", "--conds", nargs="+", default=prompts_web.CONDITIONS)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--dry-run", "--mock", action="store_true", help="fake model (mock_agent.py), no API, no cost")
    ap.add_argument("--personas", nargs="+", default=["all"], help="dry run: which mock personas")
    ap.add_argument("--offline", action="store_true", help="serve pages from web/fixtures (no network)")
    ap.add_argument("--pilot", action="store_true", help="mark as pilot (default out runs_web_pilot/)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max", "default"])
    ap.add_argument("--max-tokens", type=int, default=16000, help="per API turn (thinking counts toward it)")
    ap.add_argument("--max-steps", type=int, default=None, help="override the per-task tool-call cap")
    ap.add_argument("--time-limit", type=int, default=TIME_LIMIT_S)
    ap.add_argument("--budget-usd", type=float, default=100.0)
    ap.add_argument("--api-attempts", type=int, default=3)
    ap.add_argument("--limit", type=int, default=None, help="only do the first N pending runs")
    args = ap.parse_args()

    tlist = list(tasks) if _list(args.tasks) in ([], ["all"]) else _list(args.tasks)
    args.conditions = _list(args.conditions)
    args.models = _list(args.models)
    for t in tlist:
        if t not in tasks:
            raise SystemExit(f"unknown task {t}")
    import mock_agent
    if args.dry_run:
        personas = mock_agent.PERSONAS if _list(args.personas) in ([], ["all"]) else _list(args.personas)
        args.models = []      # the "model" of a dry run is the persona
    else:
        bad = [m for m in args.models if m not in MODELS]
        if bad:
            raise SystemExit(f"unknown model alias {bad}; choose from {list(MODELS)}")
    args.out = args.out or os.path.join(PROJECT, "runs_web_mock" if args.dry_run else
                                        ("runs_web_pilot" if args.pilot else "runs_web"))
    if not os.path.isabs(args.out):
        args.out = os.path.join(os.getcwd(), args.out)

    if not os.path.exists(KEY_JSON):
        raise SystemExit("web/answer_key.json missing: run web/answer_key.py first")
    key = json.load(open(KEY_JSON))
    if any(t["kind"] == "rank" and not t["market_equity"]["usd"] for t in tasks.values()):
        raise SystemExit("T8 market equity not frozen in tasks_web.json: run web/answer_key.py")

    # User-Agent: the test value is allowed only for dry / offline runs
    if args.offline:
        ua = sec_policy.TEST_UA
    else:
        ua = sec_policy.load_user_agent(allow_test=args.dry_run)

    client = None
    if not args.dry_run:
        import anthropic
        from dotenv import load_dotenv
        load_dotenv(os.path.join(PROJECT, ".env"))
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")
        client = anthropic.Anthropic(max_retries=5, timeout=900)

    # Jobs in repeat-major order; models (or personas) interleaved inside each cell
    jobs = []
    for rep in range(1, args.repeats + 1):
        for t in tlist:
            for c in args.conditions:
                if args.dry_run:
                    for p in personas:
                        jobs.append(dict(task=t, condition=c, model=f"mock-{p}", persona=p, repeat=rep))
                else:
                    for m in args.models:
                        jobs.append(dict(task=t, condition=c, model=m, repeat=rep))
    os.makedirs(args.out, exist_ok=True)
    pending = []
    for j in jobs:
        f = read_final(run_dir_for(args.out, j))
        if f is not None and f.get("dry_run") != args.dry_run:
            raise SystemExit(f"{run_dir_for(args.out, j)} holds a {'dry' if f['dry_run'] else 'real'} run; "
                             "use a different --out folder so dry and real runs never mix.")
        if f is None or f.get("stop_reason") == "harness_error":
            pending.append(j)
    if args.limit:
        pending = pending[:args.limit]
    log(f"{len(jobs)} runs requested, {len(jobs) - len(pending)} already done, {len(pending)} to do -> {args.out}"
        + ("  [DRY RUN]" if args.dry_run else "") + ("  [OFFLINE]" if args.offline else ""))
    write_manifest(args.out, args, len(pending))

    spent = spent_usd(args.out)
    for i, j in enumerate(pending, 1):
        if not args.dry_run:
            worst = worst_case_cost(j["model"], args.max_steps or tasks[j["task"]]["max_steps"])
            if spent + worst > args.budget_usd:
                log(f"BUDGET STOP: spent ${spent:.2f}, next run could cost up to ${worst:.2f}, "
                    f"budget ${args.budget_usd:.2f}. {len(pending) - i + 1} runs not started.")
                break
        f = do_run(j, args, client, doc, tasks, key, ua, spent_before=spent)
        if not f.get("cost_is_fake"):
            spent += f["cost_usd"]
        if f.get("error") == "budget reached mid-run":
            log(f"BUDGET STOP during {f['run_key']}: spent ${spent:.2f} of ${args.budget_usd:.2f}. "
                "That run will be redone on the next resume.")
            break
        if f.get("http_403"):
            log(f"[{i}/{len(pending)}] {f['run_key']}: SEC returned HTTP 403 (undeclared automated tool). "
                "Stopping ALL runs. Wait at least 10 minutes, check SEC_USER_AGENT, then rerun (resume-safe).")
            break
        ans = f.get("answer") or {}
        shown = ans.get("value_usd", "rank" if "ranking_high_to_low_bm" in ans else ("give_up" if ans.get("give_up") else None))
        log(f"[{i}/{len(pending)}] {f['run_key']:<34} stop={f['stop_reason']:<12} steps={f['steps']:>2} "
            f"value={shown} accn={ans.get('accession')} blocked={f['blocked_attempts']} net={f['network_requests']} "
            f"tok={f['input_tokens'] + f['cache_read_input_tokens'] + f['cache_creation_input_tokens']}/"
            f"{f['output_tokens']} ${f['cost_usd']:.4f}{' (fake)' if f['cost_is_fake'] else ''} {f['wall_s']}s"
            + (f" ERROR {f['error']}" if f.get("error") else ""))
    log(f"done. total real spend in {args.out}: ${spent_usd(args.out):.2f}")


if __name__ == "__main__":
    main()
