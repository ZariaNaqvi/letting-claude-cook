import re
import numpy as np
import pandas as pd

FILE = "6_Portfolios_ME_Prior_12_2.csv"
MARKER = "Average Value Weighted Returns -- Monthly"
MISSING = {-99.99, -999.0}


def parse_first_monthly_block(path):
    with open(path, "r", encoding="latin-1") as f:
        lines = f.read().splitlines()

    # locate the first table marker
    start = None
    for i, line in enumerate(lines):
        if MARKER in line:
            start = i
            break
    if start is None:
        raise ValueError("Marker for value-weighted monthly table not found")

    # header: first subsequent non-empty line
    j = start + 1
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    header = [p.strip() for p in lines[j].split(",")]

    # data rows
    rows = []
    k = j + 1
    started = False
    while k < len(lines):
        s = lines[k].strip()
        k += 1
        if s == "":
            if started:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if re.fullmatch(r"\d{6}", parts[0]) and len(parts) >= len(header):
            started = True
            rows.append(parts)
        else:
            if started:
                break
    return header, rows


def to_float(x):
    try:
        v = float(x)
    except ValueError:
        return np.nan
    if any(abs(v - m) < 1e-9 for m in MISSING):
        return np.nan
    return v


def main():
    header, rows = parse_first_monthly_block(FILE)

    col = {name: header.index(name) for name in
           ["SMALL HiPRIOR", "BIG HiPRIOR", "SMALL LoPRIOR", "BIG LoPRIOR"]}

    out_dates, out_vals = [], []
    for parts in rows:
        date = int(parts[0])
        sh = to_float(parts[col["SMALL HiPRIOR"]])
        bh = to_float(parts[col["BIG HiPRIOR"]])
        sl = to_float(parts[col["SMALL LoPRIOR"]])
        bl = to_float(parts[col["BIG LoPRIOR"]])
        val = 0.5 * (sh + bh) - 0.5 * (sl + bl)
        if np.isnan(val):
            continue
        out_dates.append(date)
        out_vals.append(val)

    out = pd.DataFrame({"date": out_dates, "value": out_vals})
    out["date"] = out["date"].astype(int)
    out.to_csv("output.csv", index=False, columns=["date", "value"])


if __name__ == "__main__":
    main()
