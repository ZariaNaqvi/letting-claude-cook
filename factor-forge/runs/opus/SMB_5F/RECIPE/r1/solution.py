import re
import numpy as np
import pandas as pd

FILES = ["6_Portfolios_2x3.csv", "6_Portfolios_ME_OP_2x3.csv", "6_Portfolios_ME_INV_2x3.csv"]


def read_first_monthly_vw(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    start = None
    for i, ln in enumerate(lines):
        if "Average Value Weighted Returns" in ln and "Monthly" in ln:
            start = i
            break
    if start is None:
        raise ValueError(f"VW monthly block not found in {path}")
    # header: next non-empty line
    j = start + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    header = [h.strip() for h in lines[j].split(",")]
    cols = header[1:]
    rows = []
    for ln in lines[j + 1:]:
        s = ln.strip()
        if not s:
            break
        parts = [p.strip() for p in s.split(",")]
        if not re.fullmatch(r"\d{6}", parts[0]):
            break
        vals = []
        for p in parts[1:1 + len(cols)]:
            try:
                v = float(p)
            except ValueError:
                v = np.nan
            if v <= -99.99 + 1e-9 or v == -999:
                v = np.nan
            vals.append(v)
        while len(vals) < len(cols):
            vals.append(np.nan)
        rows.append([int(parts[0])] + vals)
    df = pd.DataFrame(rows, columns=["date"] + cols).set_index("date")
    return df


def smb_from(df):
    small = [c for c in df.columns if c.upper().startswith("SMALL") or c.upper().startswith("ME1")]
    big = [c for c in df.columns if c.upper().startswith("BIG") or c.upper().startswith("ME2")]
    if len(small) != 3 or len(big) != 3:
        raise ValueError(f"Unexpected columns: {list(df.columns)}")
    s = df[small].mean(axis=1, skipna=False) - df[big].mean(axis=1, skipna=False)
    return s


series = []
for fn in FILES:
    series.append(smb_from(read_first_monthly_vw(fn)))

combined = pd.concat(series, axis=1, join="inner").dropna()
smb = combined.mean(axis=1)

out = pd.DataFrame({"date": smb.index.astype(int), "value": smb.values})
out = out.sort_values("date").reset_index(drop=True)
out.to_csv("output.csv", index=False)
