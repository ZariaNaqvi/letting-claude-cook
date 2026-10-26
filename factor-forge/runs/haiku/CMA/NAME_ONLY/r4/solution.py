import re
import numpy as np
import pandas as pd


def main():
    fname = "6_Portfolios_ME_INV_2x3.csv"
    with open(fname, encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the value-weighted monthly block
    start = None
    for i, l in enumerate(lines):
        low = l.lower()
        if "value weighted" in low and "monthly" in low:
            start = i
            break
    if start is None:
        # Fallback: treat the first block of data-looking lines as the target block
        start = -1

    # Find header line: first non-empty line after the block title
    hi = start + 1
    while hi < len(lines) and lines[hi].strip() == "":
        hi += 1
    header = [h.strip() for h in lines[hi].split(",")]

    lo_idx = [j for j, h in enumerate(header) if j > 0 and "loinv" in h.lower().replace(" ", "")]
    hi_idx = [j for j, h in enumerate(header) if j > 0 and "hiinv" in h.lower().replace(" ", "")]

    records = []
    for l in lines[hi + 1:]:
        parts = [p.strip() for p in l.split(",")]
        if not parts or not re.fullmatch(r"\d{6}", parts[0]):
            break  # end of the monthly value-weighted block
        vals = []
        for p in parts[1:1 + len(header) - 1]:
            try:
                v = float(p)
            except ValueError:
                v = np.nan
            if np.isclose(v, -99.99) or np.isclose(v, -999.0):
                v = np.nan
            vals.append(v)
        while len(vals) < len(header) - 1:
            vals.append(np.nan)
        records.append([int(parts[0])] + vals)

    cols = ["date"] + [f"c{j}" for j in range(1, len(header))]
    df = pd.DataFrame(records, columns=cols)

    lo_cols = [f"c{j}" for j in lo_idx]
    hi_cols = [f"c{j}" for j in hi_idx]

    # CMA = avg(Small LoINV, Big LoINV) - avg(Small HiINV, Big HiINV)
    df["value"] = df[lo_cols].mean(axis=1) - df[hi_cols].mean(axis=1)
    out = df[["date", "value"]].dropna()
    out["date"] = out["date"].astype(int)

    out.to_csv("output.csv", index=False, columns=["date", "value"])


if __name__ == "__main__":
    main()
