"""
Factor Forge -- human ground truth.

Rebuilds the official Fama-French factors from Ken French's RAW portfolio CSVs
and checks each one against the official factor series French publishes.

Usage:
    python -I ground_truth.py [--raw data/raw] [--out data]

Writes:
    data/truth/<TASK>.csv      official series (date YYYYMM int, value in percent)
    data/reference/<TASK>.csv  our recomputed series (same format)
    data/ground_truth_results.csv  the verification table
"""
import argparse
import os
import re
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
MISSING_CODES = (-99.99, -999.0)

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

DATA_ROW = re.compile(r"^\s*(\d{4}|\d{6})\s*,")  # YYYY (annual) or YYYYMM (monthly)


def list_blocks(path):
    """Scan a raw French CSV and return a list of table blocks.

    A block is: an optional title line (e.g. 'Average Value Weighted Returns -- Monthly'
    or 'Annual Factors: January-December'), a header line starting with ',' and then
    consecutive data rows (first field is a YYYYMM or YYYY date) until a blank line.
    Returns dicts with keys: index, title, header (list of column names),
    header_line (1-based), first_line, last_line, n_rows, freq ('monthly'/'annual').
    """
    # Split on '\n' ONLY and delete every '\r'. French files are CRLF, but some contain
    # stray lone '\r' characters mid-line (e.g. 6_Portfolios_2x3.csv has '\r,SMALL LoBM,...'
    # as a header line), and F-F_ST_Reversal_Factor.csv mixes LF-only and CRLF lines.
    # Python's default universal-newline mode would treat a lone '\r' as a line break.
    with open(path, "rb") as fh:
        text = fh.read().decode("latin-1")
    lines = [ln.replace("\r", "") for ln in text.split("\n")]
    if lines and lines[-1] == "":
        lines.pop()

    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(","):  # header row of a table
            header = [c.strip() for c in line.split(",")[1:]]
            # Title = nearest preceding non-blank, non-data lines (may span several lines)
            title_parts, j = [], i - 1
            while j >= 0 and lines[j].strip() and not DATA_ROW.match(lines[j]):
                title_parts.insert(0, lines[j].strip())
                j -= 1
            title = " ".join(title_parts) if title_parts else "(untitled, first table)"
            k = i + 1
            rows = []
            while k < len(lines) and DATA_ROW.match(lines[k]):
                rows.append(k)
                k += 1
            if rows:
                first_date = lines[rows[0]].split(",")[0].strip()
                blocks.append(dict(
                    index=len(blocks), title=title, header=header,
                    header_line=i + 1, first_line=rows[0] + 1, last_line=rows[-1] + 1,
                    n_rows=len(rows), freq="monthly" if len(first_date) == 6 else "annual",
                    first_date=first_date, last_date=lines[rows[-1]].split(",")[0].strip(),
                    _rows=rows,
                ))
            i = k
        else:
            i += 1
    for b in blocks:
        b["_lines"] = lines
    return blocks


def read_french_block(path, block_index_or_title=0):
    """Return one table block of a raw French CSV as a DataFrame of MONTHLY rows.

    block_index_or_title: int (0-based block number) or a case-insensitive
    substring of the block title (e.g. 'Value Weighted Returns -- Monthly').
    Index of the result = date as int YYYYMM; columns = header names; values in percent.
    Missing-data codes (-99.99, -999) are converted to NaN.
    Rows with more fields than the header (a real quirk of some French files)
    are truncated to the header width -- but such rows only occur in blocks we never use.
    """
    blocks = list_blocks(path)
    if isinstance(block_index_or_title, int):
        b = blocks[block_index_or_title]
    else:
        matches = [b for b in blocks if block_index_or_title.lower() in b["title"].lower()]
        if not matches:
            raise KeyError(f"no block titled like {block_index_or_title!r} in {path}")
        b = matches[0]
    if b["freq"] != "monthly":
        raise ValueError(f"block {b['index']} ({b['title']}) is annual, not monthly")
    ncol = len(b["header"])
    recs, dates = [], []
    for r in b["_rows"]:
        parts = [p.strip() for p in b["_lines"][r].split(",")]
        dates.append(int(parts[0]))
        recs.append([float(x) for x in parts[1:1 + ncol]])
    df = pd.DataFrame(recs, index=pd.Index(dates, name="date"), columns=b["header"])
    for code in MISSING_CODES:
        df = df.mask(np.isclose(df, code))
    return df


# ---------------------------------------------------------------------------
# Factor recipes (all use the VALUE-WEIGHTED MONTHLY block = block 0)
# ---------------------------------------------------------------------------

VW = "Value Weighted Returns -- Monthly"


def _p(raw, fname):
    return read_french_block(os.path.join(raw, fname), VW)


def _hi_minus_lo(df, s_hi, b_hi, s_lo, b_lo):
    return 0.5 * (df[s_hi] + df[b_hi]) - 0.5 * (df[s_lo] + df[b_lo])


def _smb3(df):
    """Average of the 3 small portfolios minus average of the 3 big portfolios."""
    small = [c for c in df.columns if c.startswith("SMALL") or c.startswith("ME1")]
    big = [c for c in df.columns if c.startswith("BIG") or c.startswith("ME2")]
    assert len(small) == 3 and len(big) == 3, df.columns
    return df[small].mean(axis=1) - df[big].mean(axis=1)


def hml(raw):
    # HML = 1/2 (Small Value + Big Value) - 1/2 (Small Growth + Big Growth)
    d = _p(raw, "6_Portfolios_2x3.csv")
    return _hi_minus_lo(d, "SMALL HiBM", "BIG HiBM", "SMALL LoBM", "BIG LoBM")


def smb_3f(raw):
    # SMB (3-factor) = 1/3 (SV + SN + SG) - 1/3 (BV + BN + BG), size x B/M sort
    return _smb3(_p(raw, "6_Portfolios_2x3.csv"))


def smb_5f(raw):
    # SMB (5-factor) = 1/3 (SMB_B/M + SMB_OP + SMB_INV), each a 3-vs-3 average
    # i.e. the average of the 9 small portfolios minus the average of the 9 big portfolios
    a = _smb3(_p(raw, "6_Portfolios_2x3.csv"))
    b = _smb3(_p(raw, "6_Portfolios_ME_OP_2x3.csv"))
    c = _smb3(_p(raw, "6_Portfolios_ME_INV_2x3.csv"))
    return (a + b + c) / 3.0


def rmw(raw):
    # RMW = 1/2 (Small Robust + Big Robust) - 1/2 (Small Weak + Big Weak)
    d = _p(raw, "6_Portfolios_ME_OP_2x3.csv")
    return _hi_minus_lo(d, "SMALL HiOP", "BIG HiOP", "SMALL LoOP", "BIG LoOP")


def cma(raw):
    # CMA = 1/2 (Small Conservative + Big Conservative) - 1/2 (Small Aggressive + Big Aggressive)
    d = _p(raw, "6_Portfolios_ME_INV_2x3.csv")
    return _hi_minus_lo(d, "SMALL LoINV", "BIG LoINV", "SMALL HiINV", "BIG HiINV")


def mom(raw):
    # Mom = 1/2 (Small High + Big High) - 1/2 (Small Low + Big Low), prior (-12,-2)
    d = _p(raw, "6_Portfolios_ME_Prior_12_2.csv")
    return _hi_minus_lo(d, "SMALL HiPRIOR", "BIG HiPRIOR", "SMALL LoPRIOR", "BIG LoPRIOR")


def st_rev(raw):
    # ST_Rev = 1/2 (Small Low + Big Low) - 1/2 (Small High + Big High), prior (-1,-1)
    d = _p(raw, "6_Portfolios_ME_Prior_1_0.csv")
    return _hi_minus_lo(d, "SMALL LoPRIOR", "BIG LoPRIOR", "SMALL HiPRIOR", "BIG HiPRIOR")


def lt_rev(raw):
    # LT_Rev = 1/2 (Small Low + Big Low) - 1/2 (Small High + Big High), prior (-60,-13)
    d = _p(raw, "6_Portfolios_ME_Prior_60_13.csv")
    return _hi_minus_lo(d, "SMALL LoPRIOR", "BIG LoPRIOR", "SMALL HiPRIOR", "BIG HiPRIOR")


# Alternative (deliberately "wrong") recipes, used only to show what is and is not official
def smb_3f_alt_9port(raw):
    return smb_5f(raw)


def smb_5f_alt_3port(raw):
    return smb_3f(raw)


# task id -> (recipe fn, official file, official column)
TASKS = {
    "HML":      (hml,     "F-F_Research_Data_Factors.csv",       "HML"),
    "SMB_3F":   (smb_3f,  "F-F_Research_Data_Factors.csv",       "SMB"),
    "SMB_5F":   (smb_5f,  "F-F_Research_Data_5_Factors_2x3.csv", "SMB"),
    "RMW":      (rmw,     "F-F_Research_Data_5_Factors_2x3.csv", "RMW"),
    "CMA":      (cma,     "F-F_Research_Data_5_Factors_2x3.csv", "CMA"),
    "MOM":      (mom,     "F-F_Momentum_Factor.csv",             "Mom"),
    "ST_REV":   (st_rev,  "F-F_ST_Reversal_Factor.csv",          "ST_Rev"),
    "LT_REV":   (lt_rev,  "F-F_LT_Reversal_Factor.csv",          "LT_Rev"),
}
ALT_TESTS = {
    # 5-factor-file HML is identical to 3-factor HML -> checked, but not a separate task
    "HML_5F(check)": (hml, "F-F_Research_Data_5_Factors_2x3.csv", "HML"),
    "SMB_3F~9port":  (smb_3f_alt_9port, "F-F_Research_Data_Factors.csv",       "SMB"),
    "SMB_5F~3port":  (smb_5f_alt_3port, "F-F_Research_Data_5_Factors_2x3.csv", "SMB"),
}


def official(raw, fname, col):
    # Official factor files: block 0 is the monthly table (its title is the file preamble)
    return read_french_block(os.path.join(raw, fname), 0)[col]


def compare(off, ref):
    j = pd.concat([off.rename("off"), ref.rename("ref")], axis=1).dropna()
    err = j["ref"] - j["off"]
    return dict(
        months=len(j), first=int(j.index.min()), last=int(j.index.max()),
        coverage=len(j) / off.notna().sum(),
        rmse_bp=float(np.sqrt((err ** 2).mean()) * 100),
        max_abs_bp=float(err.abs().max() * 100),
        n_diff_gt_1bp=int((err.abs() > 0.0100001).sum()),
        corr=float(j["ref"].corr(j["off"])),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=os.path.join(HERE, "data", "raw"))
    ap.add_argument("--out", default=os.path.join(HERE, "data"))
    ap.add_argument("--blocks", action="store_true", help="just list table blocks per file")
    a = ap.parse_args()
    if a.blocks:
        for f in sorted(os.listdir(a.raw)):
            if f.endswith(".csv"):
                print(f"## {f}")
                for b in list_blocks(os.path.join(a.raw, f)):
                    print(f"  [{b['index']}] header L{b['header_line']}, rows L{b['first_line']}-"
                          f"{b['last_line']} {b['freq']} {b['first_date']}-{b['last_date']} "
                          f"n={b['n_rows']} ncol={len(b['header'])} :: {b['title'][:75]}")
        return 0
    os.makedirs(os.path.join(a.out, "truth"), exist_ok=True)
    os.makedirs(os.path.join(a.out, "reference"), exist_ok=True)

    rows = []
    for tid, (fn, f, col) in list(TASKS.items()) + list(ALT_TESTS.items()):
        off = official(a.raw, f, col)
        ref = fn(a.raw)
        r = dict(task=tid, official=f"{f}:{col}", recipe=fn.__name__, **compare(off, ref))
        rows.append(r)
        if tid in TASKS:
            pd.DataFrame({"date": off.index, "value": off.values}).to_csv(
                os.path.join(a.out, "truth", f"{tid}.csv"), index=False)
            ref_al = ref.reindex(off.index)  # same months as official
            pd.DataFrame({"date": ref_al.index, "value": ref_al.round(4).values}).to_csv(
                os.path.join(a.out, "reference", f"{tid}.csv"), index=False)
    res = pd.DataFrame(rows)
    res.to_csv(os.path.join(a.out, "ground_truth_results.csv"), index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 20)
    print(res.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    sys.exit(main())
