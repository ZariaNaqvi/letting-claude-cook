"""
Factor Forge -- scorer self-test (no API, no cost, ~1 minute).

Plants EVERY known mistake on EVERY task (8 tasks x 11 variants = 88 scripts),
plus one script that sleeps past the time limit, runs them through the real
sandbox + scorer, and checks the scorer gives each one the right tag.

    python selftest.py          # exits with code 1 if any tag is wrong
"""
import json
import os
import sys
import tempfile

import dryrun_mock
import run_experiment as rx
import score

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")


def fake_meta(code, task, run_dir, timeout=rx.SCRIPT_TIMEOUT_S):
    meta = dict(status="done", task=task, has_code=code is not None, stop_reason="end_turn")
    if code is not None:
        meta.update(rx.run_script(code, TASKS[task]["input_files"], RAW, run_dir, timeout))
    return meta


doc = json.load(open(os.path.join(HERE, "tasks.json")))
TASKS = {t["id"]: t for t in doc["tasks"]}
refs = score.build_references(doc["tasks"])
variants = ["OK"] + dryrun_mock.BROKEN
expected = {"OK": "PASS"}
failures, n = [], 0

with tempfile.TemporaryDirectory() as tmp:
    for task in TASKS:
        for v in variants:
            # force the variant by searching for a run_key that produces it
            k = 0
            while True:
                got, text = dryrun_mock.make_response(task, f"selftest|{task}|{v}|{k}", p_ok=0.0 if v != "OK" else 1.0)
                if got == v:
                    break
                k += 1
            run_dir = os.path.join(tmp, f"{task}_{v}")
            os.makedirs(run_dir)
            code, _ = rx.extract_code(text)
            row = score.score_run(fake_meta(code, task, run_dir), run_dir, refs[task], doc["pass_rule"])
            want = expected.get(v, v)
            n += 1
            ok = row["primary_tag"] == want
            if v == "WRONG_FORMULA" and task == "SMB_5F":
                ok = ok and "SMB_SWAP" in row["tag_detail"]
            print(f"{'ok ' if ok else 'BAD'} {task:<7} {v:<17} -> {row['primary_tag']:<17} "
                  f"rmse={row['rmse_bp']:.2f}bp cov={row['coverage']:.2f} {row['tag_detail'][:50]}")
            if not ok:
                failures.append((task, v, row["primary_tag"]))

    # a script that runs too long must be tagged TIMEOUT (use a 2 s limit to keep the test fast)
    run_dir = os.path.join(tmp, "timeout")
    os.makedirs(run_dir)
    row = score.score_run(fake_meta("import time\ntime.sleep(10)\n", "HML", run_dir, timeout=2),
                          run_dir, refs["HML"], doc["pass_rule"])
    n += 1
    print(f"{'ok ' if row['primary_tag'] == 'TIMEOUT' else 'BAD'} HML     TIMEOUT           -> {row['primary_tag']}")
    if row["primary_tag"] != "TIMEOUT":
        failures.append(("HML", "TIMEOUT", row["primary_tag"]))

    # the harness must not leak the API key into the model's script
    os.environ["ANTHROPIC_API_KEY"] = "sk-test-should-not-leak"
    run_dir = os.path.join(tmp, "envleak")
    os.makedirs(run_dir)
    rx.run_script("import os\nopen('output.csv','w').write(os.environ.get('ANTHROPIC_API_KEY','none'))\n",
                  [], RAW, run_dir)
    leaked = open(os.path.join(run_dir, "output.csv")).read() != "none"
    n += 1
    print(f"{'BAD' if leaked else 'ok '} API key hidden from model script")
    if leaked:
        failures.append(("env", "API key leaked", ""))

print(f"\n{n - len(failures)}/{n} checks passed")
sys.exit(1 if failures else 0)
