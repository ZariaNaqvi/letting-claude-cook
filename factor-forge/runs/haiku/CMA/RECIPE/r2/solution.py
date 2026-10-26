import pandas as pd
import numpy as np

INPUT = "6_Portfolios_ME_INV_2x3.csv"
OUTPUT = "output.csv"
MISSING = {-99.99, -999.0}


def parse_first_vw_monthly(path):
    with open(path, encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the first value-weighted monthly block
    start = None
    for i, line in enumerate(lines):
        if "Value Weighted Returns -- Monthly" in line:
            start = i
            break
    if start is None:
        raise ValueError("Value-weighted monthly block not found")

    # Header line: begins with a comma, first field empty
    header = None
    j = start + 1
    while j < len(lines):
        s = lines[j].strip()
        if s.startswith(","):
            header = [h.strip() for h in s.split(",")][1:]
            j += 1
            break
        j += 1
    if header is None:
        raise ValueError("Header not found")

    rows = []
    started = False
    while j < len(lines):
        s = lines[j].strip()
        j += 1
        if not s:
            if started:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts[0]) != 6 or not parts[0].isdigit():
            if started:
                break
            continue
        started = True
        date = int(parts[0])
        vals = []
        for p in parts[1:1 + len(header)]:
            try:
                v = float(p)
            except ValueError:
                v = np.nan
            if v in MISSING:
                v = np.nan
            vals.append(v)
        while len(vals) < len(header):
            vals.append(np.nan)
        rows.append([date] + vals)

    df = pd.DataFrame(rows, columns=["date"] + header)
    return df


def main():
    df = parse_first_vw_monthly(INPUT)

    need = ["SMALL LoINV", "BIG LoINV", "SMALL HiINV", "BIG HiINV"]
    for c in need:
        if c not in df.columns:
            raise ValueError(f"Missing column: {c}")

    df = df.dropna(subset=need).copy()
    df["value"] = (0.5 * (df["SMALL LoINV"] + df["BIG LoINV"])
                   - 0.5 * (df["SMALL HiINV"] + df["BIG HiINV"]))

    out = df[["date", "value"]].copy()
    out["date"] = out["date"].astype(int)
    out = out.sort_values("date").reset_index(drop=True)
    out.to_csv(OUTPUT, index=False)


if __name__ == "__main__":
    main()
