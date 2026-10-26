import re
import numpy as np
import pandas as pd

SRC = "6_Portfolios_2x3.csv"
OUT = "output.csv"
MISSING = {-99.99, -999.0, -999}


def parse_value_weighted_monthly(path):
    with open(path, encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the first block header for value-weighted monthly returns
    start = None
    for i, line in enumerate(lines):
        if "value weighted returns -- monthly" in line.lower():
            start = i
            break
    if start is None:
        raise RuntimeError("Value-weighted monthly block not found")

    rows = []
    started = False
    for line in lines[start + 1:]:
        parts = [p.strip() for p in line.split(",")]
        first = parts[0] if parts else ""
        if not re.fullmatch(r"\d{6}", first):
            if started:
                break  # end of the monthly block
            continue   # skip header/blank lines before data
        if len(parts) < 7:
            if started:
                break
            continue
        started = True
        vals = []
        for p in parts[1:7]:
            try:
                v = float(p)
            except ValueError:
                v = np.nan
            if v in MISSING:
                v = np.nan
            vals.append(v)
        rows.append([int(first)] + vals)

    cols = ["date", "lo_small", "me1_small", "hi_small",
            "lo_big", "me2_big", "hi_big"]
    return pd.DataFrame(rows, columns=cols)


def main():
    df = parse_value_weighted_monthly(SRC)
    small_avg = (df["lo_small"] + df["me1_small"] + df["hi_small"]) / 3.0
    big_avg = (df["lo_big"] + df["me2_big"] + df["hi_big"]) / 3.0
    out = pd.DataFrame({
        "date": df["date"].astype(int),
        "value": small_avg - big_avg,
    })
    out = out.dropna(subset=["value"])
    out = out.drop_duplicates(subset=["date"], keep="first")
    out = out.sort_values("date").reset_index(drop=True)
    out.to_csv(OUT, index=False, columns=["date", "value"])


if __name__ == "__main__":
    main()
