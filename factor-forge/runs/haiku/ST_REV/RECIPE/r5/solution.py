import re
import numpy as np
import pandas as pd

SRC = "6_Portfolios_ME_Prior_1_0.csv"
OUT = "output.csv"
MISSING = (-99.99, -999.0)


def parse_first_vw_monthly(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    # locate the first 'Value Weighted ... Monthly' block header
    start = None
    for i, line in enumerate(lines):
        if "Average Value Weighted Returns" in line and "Monthly" in line:
            start = i
            break
    if start is None:
        raise RuntimeError("Value-weighted monthly block not found")

    # column header: next non-empty line
    j = start + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    header = [h.strip() for h in lines[j].split(",")]
    col_idx = {name: header.index(name) for name in
               ["SMALL LoPRIOR", "BIG LoPRIOR", "SMALL HiPRIOR", "BIG HiPRIOR"]}

    rows = []
    started = False
    for line in lines[j + 1:]:
        s = line.strip()
        if not s:
            if started:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if re.fullmatch(r"\d{6}", parts[0]) and len(parts) >= len(header):
            started = True
            vals = {}
            for name, k in col_idx.items():
                try:
                    v = float(parts[k])
                except ValueError:
                    v = np.nan
                if any(abs(v - m) < 1e-9 for m in MISSING):
                    v = np.nan
                vals[name] = v
            rows.append((int(parts[0]), vals))
        else:
            if started:
                break  # end of first table

    dates = [r[0] for r in rows]
    df = pd.DataFrame({
        "date": dates,
        "SL": [r[1]["SMALL LoPRIOR"] for r in rows],
        "BL": [r[1]["BIG LoPRIOR"] for r in rows],
        "SH": [r[1]["SMALL HiPRIOR"] for r in rows],
        "BH": [r[1]["BIG HiPRIOR"] for r in rows],
    })
    return df


def main():
    df = parse_first_vw_monthly(SRC)
    df = df.dropna(subset=["SL", "BL", "SH", "BH"]).copy()
    df["value"] = 0.5 * (df["SL"] + df["BL"]) - 0.5 * (df["SH"] + df["BH"])
    out = df[["date", "value"]].copy()
    out["date"] = out["date"].astype(int)
    out.to_csv(OUT, index=False)


if __name__ == "__main__":
    main()
