"""
Form Forge -- save the live pages once, for offline tests.

Walks each task's STEPS click path with the scripted `good` persona (mock_agent.py)
in RECORD mode: every response the browser receives (page HTML, the filings-list
JSON, autocomplete answers, scripts) is saved to web/fixtures/ (index.json + one
file per response). Afterwards `run_web.py --offline` and selftest_web.py serve
ONLY from these files, so tests never touch the network.

It also prints the walk, which is the check that the STEPS wording still matches
the live labels (button names, report titles). Fix tasks_web.json if a step fails.

About 40-60 requests per task at <= 5 requests/s, with SEC_USER_AGENT.

    python web/capture_fixtures.py --tasks T1 T4
    python web/capture_fixtures.py --all
"""
import argparse
import json
import os
import sys

import browser_tools as bt
import mock_agent
import prompts_web
import sec_policy

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")


def walk(task, key, ua, limiter):
    b = bt.BrowserSession(ua, mode="record", fixtures=FIXTURES, limiter=limiter)
    model = mock_agent.MockModel("good", task, key)
    messages = [{"role": "user", "content": "capture"}]
    answer = None
    try:
        for step in range(1, task["max_steps"] + 1):
            resp = model.respond(messages)
            tu = resp["content"][0]
            if tu["type"] != "tool_use":
                break
            if tu["name"] == "submit_answer":
                answer = tu["input"]
                print(f"  {step:>2} submit_answer {answer}")
                break
            obs = b.run_tool(tu["name"], tu["input"])
            first = obs.split("\n", 1)[0][:140]
            print(f"  {step:>2} {tu['name']:<10} {json.dumps(tu['input'])[:70]:<72} -> {first}")
            messages.append({"role": "assistant", "content": [tu]})
            messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tu["id"],
                                                           "content": obs}]})
            if b.policy.http_403:
                print("  SEC answered 403: stopping the capture (wait 10+ minutes, check SEC_USER_AGENT)")
                return None, b.policy.n_network, True
    finally:
        n = b.policy.n_network
        b.close()
    return answer, n, False


def main():
    doc, tasks = prompts_web.load_tasks()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks", nargs="+", default=["T1", "T4"])
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    ids = list(tasks) if a.all else a.tasks
    key = json.load(open(os.path.join(HERE, "answer_key.json")))
    ua = sec_policy.load_user_agent(allow_test=True)
    limiter = sec_policy.RateLimiter()
    ok = True
    for tid in ids:
        print(f"{tid}: {tasks[tid]['firm']}")
        ans, n, blocked = walk(tasks[tid], key["tasks"][tid], ua, limiter)
        k = key["tasks"][tid]
        if blocked:
            sys.exit(2)
        if tasks[tid]["kind"] == "rank":
            good = bool(ans) and ans.get("ranking_high_to_low_bm") == k["ranking_high_to_low_bm"]
        else:
            good = bool(ans) and ans.get("value_usd") == k["value_usd"] and ans.get("accession") == k["accession"]
        ok &= good
        print(f"  -> {'matches the key' if good else 'DOES NOT match the key'}; {n} network requests; "
              f"max {limiter.max_in_window():d} requests in any 1 s window")
    idx = json.load(open(os.path.join(FIXTURES, "index.json")))
    print(f"\nfixtures: {len(idx)} saved responses in {FIXTURES}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
