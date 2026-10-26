"""
Factor Forge -- fake model for --dry-run.

Lets you test the whole pipeline (harness -> sandbox -> scorer -> analysis)
WITHOUT an API key and without spending money.

For each run it returns a fake "model response": a markdown reply that contains
one Python script. About 70% of runs get a correct solution; the rest get a
deliberately broken variant, so the scorer's error tags can be checked:

    OK              correct script
    SIGN_FLIP       right numbers times -1
    WRONG_BLOCK     uses the equal-weighted table instead of value-weighted
    UNITS           multiplies by 100 (decimal/percent confusion)
    DATE_MISALIGN   dates shifted by one month
    PARTIAL_COVERAGE  only writes the second half of the months
    WRONG_FORMULA   uses only the small-stock legs (SMB_3F: drops neutral; SMB_5F: uses 3F recipe)
    CRASH           raises an exception
    NO_OUTPUT       runs fine but writes the wrong file name
    BAD_FORMAT      writes dates as '1926-07' strings
    NO_CODE         reply contains no code block

NOTE: this file contains working solutions to the tasks. It is NEVER shown to
the models under test; it is only used when you pass --dry-run.
"""
import hashlib
import json
import random

SMALL = ["SMALL Lo", "ME1 ", "SMALL Hi"]   # column-name prefixes of the 3 small portfolios
BIG = ["BIG Lo", "ME2 ", "BIG Hi"]

# Each task = list of (file, {column: weight}). Factor = sum over files of weighted columns.
P2x3, OP, INV = "6_Portfolios_2x3.csv", "6_Portfolios_ME_OP_2x3.csv", "6_Portfolios_ME_INV_2x3.csv"


def _hl(f, hi_s, hi_b, lo_s, lo_b):
    return [(f, {hi_s: 0.5, hi_b: 0.5, lo_s: -0.5, lo_b: -0.5})]


def _smb(f, x, w):
    cols = {"SMALL Lo" + x: w, "ME1 " + x + "2": w, "SMALL Hi" + x: w,
            "BIG Lo" + x: -w, "ME2 " + x + "2": -w, "BIG Hi" + x: -w}
    return [(f, cols)]


RECIPES = {
    "HML": _hl(P2x3, "SMALL HiBM", "BIG HiBM", "SMALL LoBM", "BIG LoBM"),
    "SMB_3F": _smb(P2x3, "BM", 1 / 3),
    "SMB_5F": _smb(P2x3, "BM", 1 / 9) + _smb(OP, "OP", 1 / 9) + _smb(INV, "INV", 1 / 9),
    "RMW": _hl(OP, "SMALL HiOP", "BIG HiOP", "SMALL LoOP", "BIG LoOP"),
    "CMA": _hl(INV, "SMALL LoINV", "BIG LoINV", "SMALL HiINV", "BIG HiINV"),
    "MOM": _hl("6_Portfolios_ME_Prior_12_2.csv", "SMALL HiPRIOR", "BIG HiPRIOR", "SMALL LoPRIOR", "BIG LoPRIOR"),
    "ST_REV": _hl("6_Portfolios_ME_Prior_1_0.csv", "SMALL LoPRIOR", "BIG LoPRIOR", "SMALL HiPRIOR", "BIG HiPRIOR"),
    "LT_REV": _hl("6_Portfolios_ME_Prior_60_13.csv", "SMALL LoPRIOR", "BIG LoPRIOR", "SMALL HiPRIOR", "BIG HiPRIOR"),
}


def _wrong_formula(task_id):
    """A plausible-but-wrong recipe for each task."""
    if task_id == "SMB_3F":                # forgot the neutral portfolios: 2-vs-2 average
        return [(P2x3, {"SMALL LoBM": 0.5, "SMALL HiBM": 0.5, "BIG LoBM": -0.5, "BIG HiBM": -0.5})]
    if task_id == "SMB_5F":
        return RECIPES["SMB_3F"]           # used the 3-factor SMB definition
    # keep only the small-stock legs (and double them): Small Hi - Small Lo
    f, w = RECIPES[task_id][0]
    return [(f, {c: 2 * v for c, v in w.items() if c.startswith("SMALL")})]


BROKEN = ["SIGN_FLIP", "WRONG_BLOCK", "UNITS", "DATE_MISALIGN", "PARTIAL_COVERAGE",
          "WRONG_FORMULA", "CRASH", "NO_OUTPUT", "BAD_FORMAT", "NO_CODE"]

SCRIPT = '''import pandas as pd

RECIPE = {recipe}
TABLE = "{table}"


def read_block(path, title):
    # split on newline only and drop CR characters (French files contain stray CRs)
    lines = open(path, "rb").read().decode("latin-1").replace("\\r", "").split("\\n")
    start = next(i for i, ln in enumerate(lines) if title in ln)
    hdr = next(i for i in range(start, len(lines)) if lines[i].startswith(","))
    cols = [c.strip() for c in lines[hdr].split(",")[1:]]
    rows = {{}}
    for ln in lines[hdr + 1:]:
        parts = [p.strip() for p in ln.split(",")]
        if not (parts[0].isdigit() and len(parts[0]) == 6):
            break
        rows[int(parts[0])] = [float(x) for x in parts[1:1 + len(cols)]]
    df = pd.DataFrame.from_dict(rows, orient="index", columns=cols)
    return df.mask(df.isin([-99.99, -999]))


total = None
for fname, weights in RECIPE:
    df = read_block(fname, TABLE)
    part = sum(w * df[c] for c, w in weights.items())
    total = part if total is None else total + part
total = total.dropna()
{mutate}
out = pd.DataFrame({{"date": {dates}, "value": total.values.round(4)}})
out.to_csv("{outname}", index=False)
print("wrote", len(out), "rows")
'''


def make_response(task_id, run_key, p_ok=0.7):
    """Return (variant, response_text) for one fake run. Deterministic per run_key."""
    seed = int(hashlib.sha256(run_key.encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    variant = "OK" if rng.random() < p_ok else rng.choice(BROKEN)

    recipe = _wrong_formula(task_id) if variant == "WRONG_FORMULA" else RECIPES[task_id]
    table = ("Equal Weighted Returns -- Monthly" if variant == "WRONG_BLOCK"
             else "Value Weighted Returns -- Monthly")
    mutate, dates, outname = "", "total.index", "output.csv"
    if variant == "SIGN_FLIP":
        mutate = "total = -total"
    elif variant == "UNITS":
        mutate = "total = total * 100"
    elif variant == "PARTIAL_COVERAGE":
        mutate = "total = total.iloc[len(total) // 2:]"
    elif variant == "DATE_MISALIGN":
        mutate = ("p = pd.PeriodIndex([pd.Period(f'{d//100}-{d%100:02d}', 'M') for d in total.index]) + 1\n"
                  "total.index = [x.year * 100 + x.month for x in p]")
    elif variant == "CRASH":
        mutate = "raise RuntimeError('could not find the right table')"
    elif variant == "NO_OUTPUT":
        outname = "factor.csv"
    elif variant == "BAD_FORMAT":
        dates = "[f'{d // 100}-{d % 100:02d}' for d in total.index]"

    code = SCRIPT.format(recipe=json.dumps(recipe, indent=1), table=table,
                         mutate=mutate, dates=dates, outname=outname)
    if variant == "NO_CODE":
        text = "I would parse the first table and compute the factor, but I cannot write the code."
    else:
        text = f"Here is the script ({variant}, dry run).\n\n```python\n{code}```\n\nIt writes output.csv."
    return variant, text
