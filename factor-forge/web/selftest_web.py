"""
Form Forge -- self-test (no API calls, no network, ~1-3 minutes).

  A. access policy: the XBRL API, /cgi-bin and other hosts are blocked; EDGAR pages are allowed
  B. rate limiter: never more than 5 requests in any 1-second window
  C. User-Agent: the harness refuses to start without SEC_USER_AGENT or with the placeholder
  D. scorer: plants EVERY mistake on EVERY task (synthetic pages + answers built from the
     frozen key) and checks each one gets the right tag
  F. API request shape: the real ClaudeCaller talks to a FAKE HTTP transport (no network, no
     key, $0) -- checks effort, caching, tools, no temperature/tool_choice, the multi-turn
     tool_use / tool_result round trip, and the cost formula
  E. end to end, offline: every mock persona on T1 and T4 through the REAL harness and the
     REAL headless browser, serving the saved pages in web/fixtures/ (skipped with a
     warning if capture_fixtures.py has not been run)

    python web/selftest_web.py            # must end with "ALL CHECKS PASSED"
"""
import json
import os
import subprocess
import sys
import tempfile

import mock_agent
import score_web
import sec_policy

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
PY = sys.executable
key = json.load(open(os.path.join(HERE, "answer_key.json")))
maps = score_web.entity_maps(key)
failures, n = [], 0


def check(ok, label):
    global n
    n += 1
    print(f"{'ok ' if ok else 'BAD'} {label}")
    if not ok:
        failures.append(label)


# ---------------------------------------------------------------- A. policy
print("A. access policy")
for url, want in [
    ("https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json", False),
    ("https://data.sec.gov/api/xbrl/frames/us-gaap/StockholdersEquity/USD/CY2026Q2I.json", False),
    ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=320193", False),
    ("https://www.sec.gov/cgi-bin/viewer?action=view&cik=320193", False),
    ("https://www.sec.gov/search/anything", False),
    ("https://fred.stlouisfed.org/series/DGS10", False),
    ("https://finance.yahoo.com/quote/AAPL", False),
    ("https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/R4.htm", True),
    ("https://www.sec.gov/edgar/browse/?CIK=320193", True),
    ("https://www.sec.gov/search-filings", True),
    ("https://data.sec.gov/submissions/CIK0000320193.json", True),
    ("https://efts.sec.gov/LATEST/search-index?keysTyped=apple", True),
]:
    got, why = sec_policy.classify(url)
    check(got == want, f"{'allow' if want else 'block'} {url[:80]}  ({why})")

# ---------------------------------------------------------------- B. rate limit
print("\nB. rate limiter")
lim = sec_policy.RateLimiter()
for _ in range(16):
    lim.acquire()
check(lim.max_in_window(1.0) <= 5, f"16 requests -> at most {lim.max_in_window(1.0)} in any 1 s window (limit 5)")

# ---------------------------------------------------------------- C. user agent
print("\nC. User-Agent")
env = {k: v for k, v in os.environ.items() if k != "SEC_USER_AGENT"}
env["FF_ENV_FILE"] = os.path.join(tempfile.gettempdir(), "ff_no_such_env_file")
p = subprocess.run([PY, os.path.join(HERE, "run_web.py"), "--dry-run", "--tasks", "T1", "--repeats", "1",
                    "--out", tempfile.mkdtemp()], env=env, capture_output=True, text=True)
check(p.returncode != 0 and "SEC_USER_AGENT" in (p.stderr + p.stdout), "run_web.py refuses to start without SEC_USER_AGENT")
env["SEC_USER_AGENT"] = sec_policy.UA_PLACEHOLDER
p = subprocess.run([PY, "-c", "import sec_policy; sec_policy.load_user_agent()"], cwd=HERE, env=env,
                   capture_output=True, text=True)
check(p.returncode != 0, "the .env.example placeholder is refused")
env["SEC_USER_AGENT"] = sec_policy.TEST_UA
p = subprocess.run([PY, "-c", "import sec_policy; sec_policy.load_user_agent()"], cwd=HERE, env=env,
                   capture_output=True, text=True)
check(p.returncode != 0, "the test User-Agent is refused for real (paid) runs")

# ---------------------------------------------------------------- D. scorer
print("\nD. scorer: planted mistakes on every task (synthetic pages)")


def fmt_m(v, scale=1_000_000):
    x = v // scale
    return f"({abs(x):,})" if x < 0 else f"{x:,}"


def score_synthetic(tid, ans, pages, visited, stop="answered"):
    tmp = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmp, "pages"))
    with open(os.path.join(tmp, "pages", "step_01.txt"), "w") as fh:
        fh.write(pages)
    final = dict(task=tid, stop_reason=stop, answer=ans, visited_urls=visited, steps=5, http_403=0)
    return score_web.score_run(final, tmp, key, maps)


def single_cases(tid, k):
    scale = 1_000 if tid in ("T4", "T5") else 1_000_000
    folder = f"https://www.sec.gov/Archives/edgar/data/{k['cik']}/{k['accession_folder']}/R4.htm"
    show = [k["value_usd"]] if k["kind"] != "common" else [k["total_stockholders_equity_usd"], k["lookalikes"]["preferred"]]
    look = list(k["lookalikes"].values()) + list(k["other_periods_same_filing"].values())
    page = (f"SEC Accession No. {k['accession']}\n$ in {'Thousands' if scale == 1000 else 'Millions'}\n"
            + "\n".join(f"Row\t{fmt_m(v, scale)}" for v in show + look if v % scale == 0))
    good = dict(value_usd=k["value_usd"], accession=k["accession"], period_end=k["period_end"])
    cases = [("PASS", good, page, [folder], "answered"),
             ("UNITS", dict(good, value_usd=k["value_usd"] // scale), page, [folder], "answered"),
             ("SIGN", dict(good, value_usd=-k["value_usd"]), page, [folder], "answered"),
             ("UNGROUNDED", dict(good, value_usd=k["value_usd"] + 123_000_000), page, [folder], "answered"),
             ("WRONG_FILING", dict(good, accession=f"{k['cik']:010d}-26-999999"), page, [folder], "answered"),
             # got lost: answered with a number it saw on an older filing, never opened the target filing
             ("NAV_ERROR", dict(good, value_usd=k["prior_period_value"], accession=f"{k['cik']:010d}-26-000001"),
              f"Row\t{fmt_m(k['prior_period_value'], scale)}\nRow\t{fmt_m(k['lookalikes'].get('preferred', 0), scale)}",
              ["https://www.sec.gov/search-filings"], "answered"),
             ("GAVE_UP", {"give_up": True}, page, [folder], "gave_up"),
             ("STEP_LIMIT", None, page, [folder], "step_limit"),
             ("TIME_LIMIT", None, page, [folder], "time_limit"),
             ("REFUSAL", None, page, [folder], "refusal"),
             ("HARNESS_ERROR", None, page, [folder], "harness_error")]
    if k["kind"] == "common":
        cases[3] = ("UNGROUNDED", cases[3][1], f"SEC Accession No. {k['accession']}", [folder], "answered")
        cases.append(("ARITH", dict(good, value_usd=k["value_usd"] - 1_000_000), page, [folder], "answered"))
    if k["other_periods_same_filing"]:
        v = next(iter(k["other_periods_same_filing"].values()))
        if v != k["value_usd"]:
            cases.append(("WRONG_PERIOD", dict(good, value_usd=v), page, [folder], "answered"))
    for name, v in k["lookalikes"].items():
        if v != k["value_usd"] and v % scale == 0 and v not in k["other_periods_same_filing"].values():
            cases.append(("WRONG_LINE", dict(good, value_usd=v), page, [folder], "answered"))
            break
    # wrong entity: another task's firm, its value and accession on the page
    other = next(o for t, o in key["tasks"].items() if o["kind"] != "rank" and o["cik"] != k["cik"])
    epage = page + f"\nSEC Accession No. {other['accession']}\nRow\t{fmt_m(other['value_usd'], 1000)}"
    cases.append(("WRONG_ENTITY", dict(good, value_usd=other["value_usd"], accession=other["accession"]),
                  epage, [folder], "answered"))
    return cases


for tid, k in key["tasks"].items():
    if k["kind"] == "rank":
        firms = k["firms"]
        page = "\n".join(f"SEC Accession No. {f['accession']}\nRow\t{fmt_m(f['value_usd'])}\n"
                         + "\n".join(f"Row\t{fmt_m(v)}" for v in f["other_periods_same_filing"].values())
                         for f in firms.values())
        visited = [f"https://www.sec.gov/Archives/edgar/data/{f['cik']}/{f['accession_folder']}/" for f in firms.values()]
        be = {t: f["value_usd"] for t, f in firms.items()}
        rk = k["ranking_high_to_low_bm"]
        tic = "KO"
        prev = next(iter(firms[tic]["other_periods_same_filing"].values()))
        cases = [("PASS", dict(book_equity_usd=be, ranking_high_to_low_bm=rk)),
                 ("ARITH", dict(book_equity_usd=be, ranking_high_to_low_bm=list(reversed(rk)))),
                 ("UNITS", dict(book_equity_usd=dict(be, AAPL=be["AAPL"] // 1_000_000), ranking_high_to_low_bm=rk)),
                 ("WRONG_PERIOD", dict(book_equity_usd=dict(be, KO=prev), ranking_high_to_low_bm=rk)),
                 ("UNGROUNDED", dict(book_equity_usd=dict(be, MMM=be["MMM"] + 77_000_000), ranking_high_to_low_bm=rk))]
        for want, ans in cases:
            row = score_synthetic(tid, ans, page, visited)
            check(row["primary_tag"] == want, f"{tid} planted {want:<13} -> {row['primary_tag']:<13} {row['tag_detail'][:60]}")
        continue
    for want, ans, page, visited, stop in single_cases(tid, k):
        row = score_synthetic(tid, ans, page, visited, stop)
        check(row["primary_tag"] == want, f"{tid} planted {want:<13} -> {row['primary_tag']:<13} {row['tag_detail'][:60]}")

# ---------------------------------------------------------------- F. API request shape
print("\nF. API request shape (fake HTTP transport, nothing leaves the machine)")
import anthropic  # noqa: E402
import httpx2  # noqa: E402

sys.path.insert(0, PROJECT)
import browser_tools as bt  # noqa: E402
import prompts_web  # noqa: E402
import run_web  # noqa: E402

bodies = []


def fake_api(request):
    bodies.append(json.loads(request.content))
    ev = [{"type": "message_start", "message": {"id": "msg_1", "type": "message", "role": "assistant",
                                                 "model": "claude-haiku-5-5", "content": [], "stop_reason": None,
                                                 "stop_sequence": None, "usage": {
                                                     "input_tokens": 10, "output_tokens": 1,
                                                     "cache_creation_input_tokens": 3000,
                                                     "cache_read_input_tokens": 500}}},
          {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": "",
                                                                         "signature": "sig"}},
          {"type": "content_block_stop", "index": 0},
          {"type": "content_block_start", "index": 1,
           "content_block": {"type": "tool_use", "id": f"toolu_{len(bodies)}", "name": "goto", "input": {}}},
          {"type": "content_block_delta", "index": 1, "delta": {
              "type": "input_json_delta", "partial_json": "{\"url\": \"https://www.sec.gov/search-filings\"}"}},
          {"type": "content_block_stop", "index": 1},
          {"type": "message_delta", "delta": {"stop_reason": "tool_use", "stop_sequence": None},
           "usage": {"output_tokens": 42}},
          {"type": "message_stop"}]
    text = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in ev)
    return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=text.encode())


client = anthropic.Anthropic(api_key="sk-test-not-a-real-key",
                             http_client=httpx2.Client(transport=httpx2.MockTransport(fake_api)))
doc, tasks = prompts_web.load_tasks()
tools = bt.TOOL_SCHEMAS + [bt.submit_tool(prompts_web.answer_schema(doc, tasks["T1"]))]
caller = run_web.ClaudeCaller(client, "claude-haiku-5-5", tools, "high", 16000)
msgs = [{"role": "user", "content": prompts_web.build_prompt(tasks["T1"], "STEPS", doc)}]
r1 = caller.respond(msgs)
uses = [run_web.block_dict(b) for b in r1["content"] if run_web.block_dict(b)["type"] == "tool_use"]
check(r1["stop_reason"] == "tool_use" and uses and uses[0]["input"] == {"url": "https://www.sec.gov/search-filings"},
      "streamed tool_use parsed (name + JSON input)")
b = bodies[0]
check(b["output_config"] == {"effort": "high"} and b["cache_control"] == {"type": "ephemeral"}
      and b["tools"][-1].get("cache_control") == {"type": "ephemeral"} and b["stream"] is True
      and b["system"][0]["text"] == prompts_web.SYSTEM_PROMPT,
      "request has effort=high, top-level cache_control, cached tool list, system prompt, streaming")
check(not ({"temperature", "tool_choice", "thinking", "top_p"} & set(b)), "no temperature / tool_choice / thinking params")
check([t["name"] for t in b["tools"]] == [t["name"] for t in tools] and len(b["tools"]) == 9, "9 tools, same order")
msgs.append({"role": "assistant", "content": r1["content"]})
msgs.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": uses[0]["id"], "content": "page"}]})
caller.respond(msgs)
m2 = bodies[1]["messages"]
check(len(m2) == 3 and m2[1]["role"] == "assistant" and m2[1]["content"][0]["type"] == "thinking"
      and m2[1]["content"][0].get("signature") == "sig" and m2[1]["content"][1]["type"] == "tool_use"
      and m2[2]["content"][0]["type"] == "tool_result",
      "turn 2 sends back thinking (with signature) + tool_use, then tool_result")
want = (10 * 0.10 + 3000 * 0.10 * 1.25 + 500 * 0.10 * 0.10 + 42 * 0.50) / 1e6
check(abs(run_web.turn_cost("haiku", r1["usage"]) - want) < 1e-12, f"cost formula (Haiku: ${want:.6f} for this turn)")
check(abs(run_web.turn_cost("fable", dict(input_tokens=0, output_tokens=0, cache_creation_input_tokens=0,
                                          cache_read_input_tokens=1_000_000)) - 0.25) < 1e-9,
      "Fable cache read = $0.25 per 1M tokens")
check(run_web.worst_case_cost("fable", 40) > run_web.worst_case_cost("haiku", 40) * 50, "worst-case budget estimate orders models")

# ---------------------------------------------------------------- E. end to end offline
print("\nE. end to end: every mock persona, real harness + headless browser, saved pages only")
fx = os.path.join(HERE, "fixtures", "index.json")
if not os.path.exists(fx):
    print("WARN fixtures missing: run `python web/capture_fixtures.py --tasks T1 T4` once (live, ~100 requests)")
    check(False, "offline end-to-end test ran")
else:
    out = tempfile.mkdtemp(prefix="ff_selftest_")
    p = subprocess.run([PY, os.path.join(HERE, "run_web.py"), "--dry-run", "--offline", "--tasks", "T1", "T4",
                        "--conds", "STEPS", "--repeats", "1", "--out", os.path.join(out, "runs_web_selftest")],
                       capture_output=True, text=True)
    print("\n".join("    " + ln for ln in p.stdout.strip().splitlines()[-20:]))
    check(p.returncode == 0, "offline dry run finished")
    p = subprocess.run([PY, os.path.join(HERE, "score_web.py"), "--runs", os.path.join(out, "runs_web_selftest"),
                        "--out", os.path.join(out, "results")], capture_output=True, text=True)
    import pandas as pd
    df = pd.read_csv(os.path.join(out, "results", "runs_scored.csv"))
    for r in df.itertuples():
        want = mock_agent.EXPECTED_TAG[r.persona]
        ok = r.primary_tag == want and (r.persona != "api" or r.blocked_attempts > 0) and r.network_requests == 0
        check(ok, f"{r.task} {r.persona:<13} -> {r.primary_tag:<13} (want {want}; blocked={r.blocked_attempts}, "
                  f"network={r.network_requests})")
    check(len(df) == 2 * len(mock_agent.PERSONAS), f"{len(df)} offline runs scored")

print(f"\n{n - len(failures)}/{n} checks passed")
print("ALL CHECKS PASSED" if not failures else "FAILED: " + "; ".join(failures[:10]))
sys.exit(1 if failures else 0)
