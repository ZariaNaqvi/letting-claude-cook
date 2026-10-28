"""
Form Forge -- automatic scorer.

Reads every finished run (final.json) under --runs, compares the submitted answer
with the FROZEN key (web/answer_key.json) and writes one row per run to
<out>/runs_scored.csv.

PASS = all three:
  1. the run ended with submit_answer and give_up was not set
  2. value_usd == key exactly (tolerance 0). T8: all four book equities exact AND the ranking exact
  3. the accession is the original filing for that period (or its /A amendment). T8: not checked

Error tags (primary_tag = the first that matches, in this order):
  HARNESS_ERROR  harness exception or site outage/403 -> excluded from analysis and rerun
  STEP_LIMIT     hit the tool-call cap without an answer
  TIME_LIMIT     hit the 12-minute cap
  REFUSAL        the API stopped with stop_reason "refusal"
  GAVE_UP        give_up=true, or the model stopped calling tools without an answer
  UNGROUNDED     the submitted number never appeared in any page the run saw (any display
                 form: 107,520 / 107,520,000 / 107520000000 / (3,982,431)). T6: also grounded if
                 both components appear. Checked BEFORE NAV_ERROR so a guess is called a guess
  WRONG_ENTITY   the accession belongs to another company, or the value is another company's
                 value in the frames snapshot (checked before NAV_ERROR: a model that got the
                 wrong company also never reached the right filing)
  NAV_ERROR      never reached the target filing: its folder is in no visited URL and its
                 accession is in no observation
  UNITS          value / key is 10^3, 10^6, 10^-3 or 10^-6
  SIGN           value == -key
  WRONG_PERIOD   value = the same company's equity at another date (comparative column, prior quarter)
  WRONG_LINE     value = a look-alike line for the same date (incl. NCI, total liabilities + equity,
                 preferred not subtracted, liquidation preference, total assets)
  WRONG_FILING   value right, accession wrong (e.g. a later filing that repeats the number)
  ARITH          T6/T8: the inputs were seen / correct, but the subtraction or ranking is wrong
  OTHER_WRONG    anything else (read these by hand)

    python web/score_web.py --runs runs_web_mock --out results_web_mock
"""
import argparse
import glob
import json
import os
import re

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
KEY_JSON = os.path.join(HERE, "answer_key.json")
FAILURE_ORDER = ["HARNESS_ERROR", "STEP_LIMIT", "TIME_LIMIT", "REFUSAL", "GAVE_UP", "UNGROUNDED", "WRONG_ENTITY",
                 "NAV_ERROR", "UNITS", "SIGN", "WRONG_PERIOD", "WRONG_LINE", "WRONG_FILING", "ARITH",
                 "OTHER_WRONG"]
FINANCE_NAV_TAGS = ["WRONG_LINE", "WRONG_PERIOD", "UNITS", "SIGN", "WRONG_ENTITY", "WRONG_FILING", "NAV_ERROR"]


# ---------------------------------------------------------------------------
# Grounding: did the number appear on a page the model saw?
# ---------------------------------------------------------------------------
def display_forms(v):
    """How a whole-dollar value can be printed on an R page (millions, thousands, dollars, billions)."""
    v = abs(int(v))
    out = set()
    for scale in (1, 1_000, 1_000_000, 1_000_000_000):
        if v % scale == 0:
            x = v // scale
            if len(str(x)) >= 4:                     # too-short numbers match by accident
                out.add(f"{x:,}")
                out.add(str(x))
    return out


def appears(v, text):
    for f in display_forms(v):
        if re.search(r"(?<![\d,.])" + re.escape(f) + r"(?![\d,]|\.\d)", text):
            return True
    return False


def as_int(x):
    try:
        if isinstance(x, bool):
            return None
        if isinstance(x, str):
            x = x.replace(",", "").replace("$", "").strip()
        return int(round(float(x)))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Per-firm diagnosis
# ---------------------------------------------------------------------------
def entity_maps(key):
    by_accn, by_val = {}, {}
    for r in key["frames_snapshot"]:
        by_accn[r["accn"]] = r["cik"]
        by_val.setdefault(r["val"], set()).add(r["cik"])
    for t in key["tasks"].values():
        for fk in (t["firms"].values() if t["kind"] == "rank" else [t]):
            by_accn[fk["accession"]] = fk["cik"]
    return by_accn, by_val


def diagnose(v, accn, fk, pages, visited, maps, check_accn=True):
    """Return (tag or 'PASS', detail) for one submitted value against one firm's key."""
    by_accn, by_val = maps
    k = fk["value_usd"]
    accn_ok = (not check_accn) or (accn in fk["allowed_accessions"])
    if v == k and accn_ok:
        return "PASS", ""
    grounded = appears(v, pages)
    if fk.get("kind") == "common" and not grounded:
        grounded = appears(fk["total_stockholders_equity_usd"], pages) and appears(fk["lookalikes"]["preferred"], pages)
    if not grounded:
        return "UNGROUNDED", f"{v:,} not on any page"
    other_cik = by_accn.get(accn)
    if (other_cik is not None and other_cik != fk["cik"]) or (by_val.get(v, set()) - {fk["cik"]} and v != k):
        return "WRONG_ENTITY", f"accession/value of CIK {other_cik or sorted(by_val.get(v))}"
    reached = any(fk["accession_folder"] in u for u in visited) or fk["accession"] in pages
    if not reached:
        return "NAV_ERROR", f"never reached {fk['accession']}"
    if k != 0 and v != 0:
        r = v / k
        for s in (1e3, 1e6, 1e-3, 1e-6):
            if abs(r / s - 1) < 1e-9:
                return "UNITS", f"x{s:g}"
    if v == -k:
        return "SIGN", "sign flipped"
    others = dict(fk["other_periods_same_filing"])
    if fk.get("prior_period_value") is not None:
        others[fk["prior_period_end"]] = fk["prior_period_value"]
    for end, val in others.items():
        if v == val:
            return "WRONG_PERIOD", f"value at {end}"
    for name, val in fk["lookalikes"].items():
        if v == val:
            return "WRONG_LINE", name
    if v == k and not accn_ok:
        return "WRONG_FILING", f"accession {accn}" + (" (later filing)" if accn in fk["later_filings_same_value"] else "")
    if fk.get("kind") == "common":
        return "ARITH", "components seen, combination wrong"
    return "OTHER_WRONG", f"{v:,}"


def read_pages(run_dir):
    texts = []
    for p in sorted(glob.glob(os.path.join(run_dir, "pages", "step_*.txt"))):
        with open(p) as fh:
            texts.append(fh.read())
    return "\n".join(texts)


def score_run(final, run_dir, key, maps):
    tid = final["task"]
    tk = key["tasks"][tid]
    row = {k: final.get(k) for k in (
        "run_key", "task", "condition", "model_alias", "model_id", "repeat", "persona", "dry_run", "pilot",
        "stop_reason", "steps", "turns", "input_tokens", "output_tokens", "cache_creation_input_tokens",
        "cache_read_input_tokens", "cost_usd", "cost_is_fake", "wall_s", "blocked_attempts",
        "visited_search_form", "network_requests", "http_403", "prompt_sha", "prompt_version")}
    row.update(passed=False, value_ok=False, accn_ok=False, period_ok=False, grounded=False,
               primary_tag="", tag_detail="", submitted_value="", submitted_accession="")
    stop, ans = final.get("stop_reason"), final.get("answer") or {}
    pages = read_pages(run_dir)
    visited = final.get("visited_urls") or []

    if stop == "harness_error" or (final.get("http_403") or 0) > 0:
        tag, detail = "HARNESS_ERROR", str(final.get("error") or "SEC 403")[:150]
    elif stop == "step_limit":
        tag, detail = "STEP_LIMIT", f"{final.get('steps')} steps"
    elif stop == "time_limit":
        tag, detail = "TIME_LIMIT", f"{final.get('wall_s')} s"
    elif stop == "refusal":
        tag, detail = "REFUSAL", str(final.get("refusal_category"))
    elif stop != "answered" or ans.get("give_up"):
        tag, detail = "GAVE_UP", str(ans.get("evidence_url") or stop)[:150]
    elif tk["kind"] == "rank":
        tag, detail = score_rank(ans, tk, pages, visited, maps, row)
    else:
        v, accn = as_int(ans.get("value_usd")), str(ans.get("accession") or "").strip()
        row.update(submitted_value=v, submitted_accession=accn)
        if v is None:
            tag, detail = "OTHER_WRONG", f"unreadable value {ans.get('value_usd')!r}"
        else:
            row["value_ok"] = v == tk["value_usd"]
            row["accn_ok"] = accn in tk["allowed_accessions"]
            row["period_ok"] = str(ans.get("period_end") or "") == tk["period_end"]
            row["grounded"] = appears(v, pages)
            tag, detail = diagnose(v, accn, tk, pages, visited, maps)
    row["passed"] = tag == "PASS"
    row.update(primary_tag=tag, tag_detail=detail)
    return row


def score_rank(ans, tk, pages, visited, maps, row):
    be = ans.get("book_equity_usd") or {}
    ranking = [str(x).upper() for x in (ans.get("ranking_high_to_low_bm") or [])]
    firm_tags = {}
    for tic, fk in tk["firms"].items():
        v = as_int(be.get(tic))
        firm_tags[tic] = ("OTHER_WRONG", "missing") if v is None else \
            diagnose(v, fk["accession"], fk, pages, visited, maps, check_accn=False)
    all_ok = all(t == "PASS" for t, _ in firm_tags.values())
    row["value_ok"] = all_ok
    row["grounded"] = all(as_int(be.get(t)) is not None and appears(as_int(be.get(t)), pages) for t in tk["firms"])
    row["submitted_value"] = json.dumps(be)
    if all_ok and ranking == tk["ranking_high_to_low_bm"]:
        return "PASS", ""
    if all_ok:
        return "ARITH", f"ranking {ranking} != {tk['ranking_high_to_low_bm']}"
    bad = [(FAILURE_ORDER.index(t), tic, t, d) for tic, (t, d) in firm_tags.items() if t != "PASS"]
    _, tic, t, d = min(bad)
    return t, f"{tic}: {d} ({len(bad)} firm(s) wrong)"


def main():
    ap = argparse.ArgumentParser(description="Score Form Forge runs against the frozen key.")
    ap.add_argument("--runs", default=os.path.join(PROJECT, "runs_web"))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    runs = a.runs if os.path.isabs(a.runs) else os.path.join(os.getcwd(), a.runs)
    out = a.out or runs.replace("runs_web", "results_web")
    out = out if os.path.isabs(out) else os.path.join(os.getcwd(), out)
    os.makedirs(out, exist_ok=True)
    key = json.load(open(KEY_JSON))
    maps = entity_maps(key)

    rows = []
    for d in sorted(os.listdir(runs)):
        p = os.path.join(runs, d, "final.json")
        if os.path.exists(p):
            rows.append(score_run(json.load(open(p)), os.path.join(runs, d), key, maps))
    if not rows:
        raise SystemExit(f"no runs found in {runs}")
    df = pd.DataFrame(rows).sort_values(["task", "condition", "model_alias", "repeat"])
    df.to_csv(os.path.join(out, "runs_scored.csv"), index=False)
    print(f"scored {len(df)} runs from {runs} (PASS = answered, exact value, original accession)")
    print(df["primary_tag"].value_counts().to_string())

    # Dry run: we KNOW which mistake each persona planted -- check the tags agree
    if df["persona"].notna().any():
        import mock_agent
        df["expected_tag"] = df["persona"].map(mock_agent.EXPECTED_TAG)
        ok = df["expected_tag"] == df["primary_tag"]
        api = df["persona"] == "api"
        ok &= ~api | (df["blocked_attempts"] > 0)
        check = pd.crosstab(df["persona"], df["primary_tag"])
        check.to_csv(os.path.join(out, "dryrun_check.csv"))
        print("\nDry-run check: planted persona (rows) vs scorer's primary tag (columns)")
        print(check.to_string())
        bad = df[~ok]
        print(f"\n{len(bad)} mismatches" + ("" if bad.empty else ":\n" + bad[
            ["run_key", "persona", "expected_tag", "primary_tag", "tag_detail"]].to_string(index=False)))
    print(f"\nwrote {os.path.join(out, 'runs_scored.csv')}")


if __name__ == "__main__":
    main()
