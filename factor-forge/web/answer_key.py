"""
Form Forge -- the answer key (independent of the pages the models see).

Source: SEC's XBRL API, which the models' browser CANNOT reach (sec_policy blocks
data.sec.gov/api/xbrl). For each company: one companyfacts request; plus one
frames request (StockholdersEquity, CY2026Q2I) used to detect WRONG_ENTITY answers.
11 requests in total, 0.3 s apart, with the declared User-Agent.

For each task it picks the StockholdersEquity fact with
    end == target_end, form in allowed_forms, filed in the July-August 2026 window,
and the EARLIEST filed date (the original filing, not a later filing that repeats
the number as a comparative). It also records the look-alike numbers that the
scorer uses to name mistakes:
    other end dates in the same filing (comparative column)    -> WRONG_PERIOD
    equity incl. noncontrolling interest, total L+E, preferred -> WRONG_LINE
    later filings that repeat the same number                  -> WRONG_FILING
    other companies' values in the frames snapshot             -> WRONG_ENTITY

Outputs
    web/data/raw/*.json.gz      raw API responses (gzip), with sha256 of the raw bytes
    web/data/raw/manifest.json  url, fetch time, sha256, bytes
    web/answer_key.json         the frozen key (scoring reads only this file)
    web/tasks_web.json          the "answer" block of each task is filled in

    python web/answer_key.py --out web/answer_key.json    # fetch (~11 requests) and freeze
    python web/answer_key.py --check                      # no network: re-verify sha256, rebuild, compare
"""
import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import sys
import time

import sec_policy

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")
TASKS_JSON = os.path.join(HERE, "tasks_web.json")
KEY_JSON = os.path.join(HERE, "answer_key.json")
FRAME = "CY2026Q2I"
LOOKALIKE_CONCEPTS = {
    "incl_nci": "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    "total_liabilities_and_equity": "LiabilitiesAndStockholdersEquity",
    "preferred": ["PreferredStockValue", "PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount",
                  "PreferredStockIncludingAdditionalPaidInCapital"],   # first one present wins
    "preferred_liquidation": "PreferredStockLiquidationPreferenceValue",
    "total_assets": "Assets",
}


def load_tasks():
    with open(TASKS_JSON) as fh:
        return json.load(fh)


def all_ciks(doc):
    ciks = set()
    for t in doc["tasks"]:
        if t["kind"] == "rank":
            ciks |= {f["cik"] for f in t["firms"]}
        else:
            ciks.add(t["cik"])
    return sorted(ciks)


# ---------------------------------------------------------------------------
# Fetching (network) and reading back (no network)
# ---------------------------------------------------------------------------
def raw_name(url):
    tail = url.rstrip("/").split("/")
    return ("frames_" + "_".join(tail[-4:]) if "/frames/" in url else tail[-1]).replace(".json", "") + ".json.gz"


def fetch_all(urls, ua):
    import httpx2
    os.makedirs(RAW, exist_ok=True)
    manifest = {}
    with httpx2.Client(headers={"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}, timeout=60) as c:
        for i, url in enumerate(urls):
            if i:
                time.sleep(0.3)          # ~3 requests/s, well under SEC's 10/s
            r = c.get(url)
            r.raise_for_status()
            body = r.content
            name = raw_name(url)
            with gzip.open(os.path.join(RAW, name), "wb") as fh:
                fh.write(body)
            manifest[name] = dict(url=url, fetched_at=dt.datetime.now().isoformat(timespec="seconds"),
                                  sha256=hashlib.sha256(body).hexdigest(), bytes=len(body))
            print(f"  fetched {url}  ({len(body):,} bytes)")
    with open(os.path.join(RAW, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    return manifest


def read_raw(name, manifest):
    with gzip.open(os.path.join(RAW, name), "rb") as fh:
        body = fh.read()
    sha = hashlib.sha256(body).hexdigest()
    if sha != manifest[name]["sha256"]:
        raise SystemExit(f"sha256 mismatch for {name}: raw file changed since it was fetched")
    return json.loads(body)


# ---------------------------------------------------------------------------
# Building the key
# ---------------------------------------------------------------------------
def facts(cf, concept, taxonomy="us-gaap", unit="USD"):
    try:
        return cf["facts"][taxonomy][concept]["units"][unit]
    except KeyError:
        return []


def in_window(f, window):
    return window[0] <= f["filed"] <= window[1]


def pick(cf, end, forms, window, concept="StockholdersEquity"):
    """The original filing's fact for this end date (earliest filed in the window)."""
    cands = [f for f in facts(cf, concept) if f["end"] == end and f["form"] in forms and in_window(f, window)]
    if not cands:
        raise SystemExit(f"{cf.get('entityName')}: no {concept} fact for end={end}, forms={forms}, filed in {window}")
    cands.sort(key=lambda f: (f["filed"], f["accn"]))
    return cands[0]


def firm_key(cf, end, forms, window):
    f = pick(cf, end, forms, window)
    accn = f["accn"]
    se = facts(cf, "StockholdersEquity")
    same_filing = {g["end"]: g["val"] for g in se if g["accn"] == accn and g["end"] != end}
    prior = sorted((g for g in se if g["end"] < end and g["form"].startswith("10-")), key=lambda g: g["end"])
    look = {}
    for k, concepts in LOOKALIKE_CONCEPTS.items():
        for concept in ([concepts] if isinstance(concepts, str) else concepts):
            v = [g["val"] for g in facts(cf, concept) if g["accn"] == accn and g["end"] == end]
            if v:
                look[k] = v[0]
                break
    later = sorted({g["accn"] for g in se if g["end"] == end and g["val"] == f["val"] and g["accn"] != accn})
    amends = sorted({g["accn"] for g in se if g["end"] == end and g["form"].endswith("/A")})
    shares = [g["val"] for g in facts(cf, "EntityCommonStockSharesOutstanding", "dei", "shares")
              if g["accn"] == accn]
    return dict(cik=int(cf["cik"]), entity=cf["entityName"], value_usd=int(f["val"]), accession=accn,
                accession_folder=accn.replace("-", ""), form=f["form"], filed=f["filed"], period_end=end,
                fy=f.get("fy"), fp=f.get("fp"), allowed_accessions=[accn] + amends,
                other_periods_same_filing=same_filing,
                prior_period_value=prior[-1]["val"] if prior else None,
                prior_period_end=prior[-1]["end"] if prior else None,
                lookalikes=look, later_filings_same_value=later,
                cover_shares_outstanding=int(sum(shares)) if shares else None)


def build_key(doc, read):
    window = doc["filed_window"]
    frames = read(raw_name(frame_url()))
    key = dict(built_at=dt.datetime.now().isoformat(timespec="seconds"), frame=FRAME,
               source="data.sec.gov/api/xbrl companyfacts + frames (blocked for the models)",
               tasks={}, frames_snapshot=[dict(cik=r["cik"], entity=r["entityName"], accn=r["accn"],
                                              val=r["val"], end=r["end"]) for r in frames["data"]])
    for t in doc["tasks"]:
        if t["kind"] == "rank":
            firms = {}
            for fm in t["firms"]:
                cf = read(raw_name(cf_url(fm["cik"])))
                firms[fm["ticker"]] = firm_key(cf, fm["target_end"], t["allowed_forms"], window)
            me_cfg = t["market_equity"]
            me = {}
            for tic, k in firms.items():
                if me_cfg.get("usd", {}).get(tic):
                    me[tic] = int(me_cfg["usd"][tic])
                else:
                    me[tic] = int(round(k["cover_shares_outstanding"] * me_cfg["close_2026_06_30"][tic]))
            bm = {tic: firms[tic]["value_usd"] / me[tic] for tic in firms}
            ranking = sorted(bm, key=lambda x: -bm[x])
            key["tasks"][t["id"]] = dict(kind="rank", firms=firms, market_equity_usd=me,
                                         book_to_market={k: round(v, 6) for k, v in bm.items()},
                                         ranking_high_to_low_bm=ranking)
            continue
        cf = read(raw_name(cf_url(t["cik"])))
        k = firm_key(cf, t["target_end"], t["allowed_forms"], window)
        k["kind"] = t["kind"]
        if t["kind"] == "common":
            pref = k["lookalikes"].get("preferred")
            if not pref:
                raise SystemExit(f"{t['id']}: PreferredStockValue missing for {k['accession']}")
            k["total_stockholders_equity_usd"] = k["value_usd"]
            k["value_usd"] = k["value_usd"] - pref
            k["lookalikes"]["total_se_preferred_not_subtracted"] = k["total_stockholders_equity_usd"]
            if k["lookalikes"].get("preferred_liquidation"):
                k["lookalikes"]["se_minus_liquidation_preference"] = \
                    k["total_stockholders_equity_usd"] - k["lookalikes"]["preferred_liquidation"]
        key["tasks"][t["id"]] = k
    return key


def cf_url(cik):
    return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json"


def frame_url():
    return f"https://data.sec.gov/api/xbrl/frames/us-gaap/StockholdersEquity/USD/{FRAME}.json"


def write_answers_into_tasks(doc, key):
    for t in doc["tasks"]:
        k = key["tasks"][t["id"]]
        if t["kind"] == "rank":
            t["answer"] = {"book_equity_usd": {tic: f["value_usd"] for tic, f in k["firms"].items()},
                           "accessions": {tic: f["accession"] for tic, f in k["firms"].items()},
                           "ranking_high_to_low_bm": k["ranking_high_to_low_bm"]}
            t["market_equity"]["usd"] = k["market_equity_usd"]
        else:
            t["answer"] = {"value_usd": k["value_usd"], "accession": k["accession"],
                           "period_end": k["period_end"], "form": k["form"], "filed": k["filed"]}
        t["tolerance_usd"] = 0
    with open(TASKS_JSON + ".tmp", "w") as fh:
        json.dump(doc, fh, indent=2)
    os.replace(TASKS_JSON + ".tmp", TASKS_JSON)


def print_table(key):
    print(f"\n{'task':<5} {'entity':<28} {'value_usd':>18} {'accession':<22} {'form':<5} {'filed':<10} end")
    for tid, k in key["tasks"].items():
        if k["kind"] == "rank":
            for tic, f in k["firms"].items():
                print(f"{tid:<5} {tic + ' ' + f['entity'][:23]:<28} {f['value_usd']:>18,} {f['accession']:<22} "
                      f"{f['form']:<5} {f['filed']:<10} {f['period_end']}  ME={k['market_equity_usd'][tic]:,} "
                      f"B/M={k['book_to_market'][tic]:.4f}")
            print(f"{tid:<5} ranking high->low B/M: {k['ranking_high_to_low_bm']}")
        else:
            extra = f"  (SE {k['total_stockholders_equity_usd']:,} - preferred {k['lookalikes']['preferred']:,})" \
                if k["kind"] == "common" else ""
            print(f"{tid:<5} {k['entity'][:28]:<28} {k['value_usd']:>18,} {k['accession']:<22} {k['form']:<5} "
                  f"{k['filed']:<10} {k['period_end']}{extra}")
            print(f"{'':<5} look-alikes: {k['lookalikes']}  other periods: {k['other_periods_same_filing']}  "
                  f"later same-value filings: {k['later_filings_same_value']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=KEY_JSON)
    ap.add_argument("--check", action="store_true", help="no network: verify raw files and the frozen key")
    ap.add_argument("--rebuild", action="store_true", help="no network: rebuild the key from raw files")
    ap.add_argument("--force", action="store_true", help="overwrite an existing frozen key")
    a = ap.parse_args()
    doc = load_tasks()
    urls = [cf_url(c) for c in all_ciks(doc)] + [frame_url()]

    if a.check or a.rebuild:
        manifest = json.load(open(os.path.join(RAW, "manifest.json")))
        key = build_key(doc, lambda n: read_raw(n, manifest))
        print(f"sha256 OK for {len(manifest)} raw files")
        if a.check:
            frozen = json.load(open(a.out))
            same = all(frozen["tasks"][t] == json.loads(json.dumps(key["tasks"][t])) for t in key["tasks"])
            print_table(frozen)
            print("\nfrozen key matches a rebuild from raw files:", same)
            sys.exit(0 if same else 1)
    else:
        if os.path.exists(a.out) and not a.force:
            raise SystemExit(f"{a.out} exists (frozen). Use --check, or --force to refetch and overwrite.")
        ua = sec_policy.load_user_agent(allow_test=True)
        print(f"fetching {len(urls)} SEC API files (UA sha256 {sec_policy.ua_digest(ua)[:12]}...)")
        manifest = fetch_all(urls, ua)
        key = build_key(doc, lambda n: read_raw(n, manifest))
    key["raw_manifest_sha256"] = hashlib.sha256(
        open(os.path.join(RAW, "manifest.json"), "rb").read()).hexdigest()
    with open(a.out + ".tmp", "w") as fh:
        json.dump(key, fh, indent=1)
    os.replace(a.out + ".tmp", a.out)
    write_answers_into_tasks(doc, key)
    print_table(key)
    print(f"\nwrote {a.out} and the answer blocks in {TASKS_JSON}")


if __name__ == "__main__":
    main()
