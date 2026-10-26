import re
import numpy as np
import pandas as pd

FILES = ["6_Portfolios_2x3.csv", "6_Portfolios_ME_OP_2x3.csv", "6_Portfolios_ME_INV_2x3.csv"]


def read_first_vw_monthly(path):
    with open(path, "r", encoding="latin-1") as f:
        lines = [l.rstrip("\r\n") for l in f]
    start = None
    for i, l in enumerate(lines):
        if "Average Value Weighted Returns" in l and "Monthly" in l:
            start = i
            break
    if start is None:
        raise ValueError("VW monthly block not found in " + path)
    # header line: next non-empty line
    j = start + 1
    while not lines[j].strip():
        j += 1
    header = [h.strip() for h in lines[j].split(",")]
    cols = header[1:]
    rows = []
    for l in lines[j + 1:]:
        s = l.strip()
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
            if v <= -99.99 or v == -999:
                v = np.nan
            vals.append(v)
        rows.append([int(parts[0])] + vals)
    df = pd.DataFrame(rows, columns=["date"] + cols).set_index("date")
    return df


def smb_component(df):
    small = [c for c in df.columns if c.upper().startswith("SMALL") or c.upper().startswith("ME1")]
    big = [c for c in df.columns if c.upper().startswith("BIG") or c.upper().startswith("ME2")]
    if len(small) != 3 or len(big) != 3:
        # fallback to positional
        small = list(df.columns[:3])
        big = list(df.columns[3:6])
    return df[small].mean(axis=1, skipna=False) - df[big].mean(axis=1, skipna=False)


comps = [smb_component(read_first_vw_monthly(f)) for f in FILES]
combined = pd.concat(comps, axis=1, join="inner").dropna()
smb = combined.mean(axis=1)

out = pd.DataFrame({"date": smb.index.astype(int), "value": smb.values})
out = out.sort_values("date")
out.to_csv("output.csv", index=False)
