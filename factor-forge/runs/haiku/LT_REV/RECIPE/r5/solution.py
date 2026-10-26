import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_ME_Prior_60_13.csv"
OUT = "output.csv"


def main():
    with open(FNAME, encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the FIRST block: 'Average Value Weighted Returns -- Monthly'
    start = None
    for i, l in enumerate(lines):
        if "Average Value Weighted Returns" in l and "Monthly" in l:
            start = i
            break
    if start is None:
        raise RuntimeError("Monthly value-weighted block not found")

    # Header line (skip blank lines after the title)
    j = start + 1
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    header = [h.strip() for h in lines[j].split(",")]
    j += 1

    # Collect monthly rows until the block ends
    rows = []
    while j < len(lines):
        parts = [p.strip() for p in lines[j].split(",")]
        if not parts or not re.fullmatch(r"\d{6}", parts[0]):
            break
        rows.append(parts)
        j += 1

    # Identify columns by name; fall back to known positions
    def col_idx(name, fallback):
        return header.index(name) if name in header else fallback

    i_sl = col_idx("SMALL LoPRIOR", 1)
    i_sh = col_idx("SMALL HiPRIOR", 3)
    i_bl = col_idx("BIG LoPRIOR", 4)
    i_bh = col_idx("BIG HiPRIOR", 6)

    def to_num(s):
        try:
            v = float(s)
        except ValueError:
            return np.nan
        if v in (-99.99, -999.0):
            return np.nan
        return v

    out_dates, out_vals = [], []
    for parts in rows:
        if max(i_sl, i_sh, i_bl, i_bh) >= len(parts):
            continue
        sl = to_num(parts[i_sl])
        sh = to_num(parts[i_sh])
        bl = to_num(parts[i_bl])
        bh = to_num(parts[i_bh])
        val = 0.5 * (sl + bl) - 0.5 * (sh + bh)
        if np.isnan(val):
            continue
        out_dates.append(int(parts[0]))
        out_vals.append(val)

    result = pd.DataFrame({"date": out_dates, "value": out_vals})
    result.to_csv(OUT, index=False)


if __name__ == "__main__":
    main()
