import csv
import re

import numpy as np
import pandas as pd

SRC = "6_Portfolios_2x3.csv"
OUT = "output.csv"

SMALL_COLS = ["SMALL LoBM", "ME1 BM2", "SMALL HiBM"]
BIG_COLS = ["BIG LoBM", "ME2 BM2", "BIG HiBM"]
MISSING = {-99.99, -999.0}


def norm(s):
    return " ".join(str(s).strip().split())


def main():
    with open(SRC, encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the first value-weighted monthly block
    start = None
    for i, line in enumerate(lines):
        low = line.lower()
        if "value weighted returns" in low and "monthly" in low:
            start = i
            break
    if start is None:
        raise RuntimeError("Value-weighted monthly block not found")

    # Column header is the next non-empty line
    j = start + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    header = [norm(x) for x in next(csv.reader([lines[j]]))]
    col_idx = {name: k for k, name in enumerate(header)}
    for name in SMALL_COLS + BIG_COLS:
        if name not in col_idx:
            raise RuntimeError(f"Column {name!r} not found in header {header}")

    # Read data rows until the block ends
    rows = []
    for line in lines[j + 1:]:
        if not line.strip():
            if rows:
                break
            continue
        fields = next(csv.reader([line]))
        first = fields[0].strip()
        if not re.fullmatch(r"\d{6}", first):
            if rows:
                break
            continue
        vals = []
        for name in SMALL_COLS + BIG_COLS:
            raw = fields[col_idx[name]].strip()
            try:
                v = float(raw)
            except ValueError:
                v = np.nan
            if v in MISSING:
                v = np.nan
            vals.append(v)
        rows.append([int(first)] + vals)

    cols = ["date"] + SMALL_COLS + BIG_COLS
    df = pd.DataFrame(rows, columns=cols)
    df = df.drop_duplicates(subset="date", keep="first").sort_values("date")

    small = df[SMALL_COLS].mean(axis=1, skipna=False)
    big = df[BIG_COLS].mean(axis=1, skipna=False)
    out = pd.DataFrame({"date": df["date"].astype(int), "value": small - big})
    out = out.dropna(subset=["value"])
    out["date"] = out["date"].astype(int)

    out.to_csv(OUT, index=False, columns=["date", "value"])


if __name__ == "__main__":
    main()
