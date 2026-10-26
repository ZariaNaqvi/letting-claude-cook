import re
import numpy as np
import pandas as pd

FILES = ["6_Portfolios_2x3.csv", "6_Portfolios_ME_OP_2x3.csv", "6_Portfolios_ME_INV_2x3.csv"]


def read_first_block(path):
    with open(path, "r", encoding="latin-1") as f:
        lines = f.read().splitlines()
    start = None
    for i, ln in enumerate(lines):
        if "Average Value Weighted Returns -- Monthly" in ln:
            start = i
            break
    if start is None:
        raise ValueError(f"Block not found in {path}")
    header = [h.strip() for h in lines[start + 1].split(",")]
    cols = header[1:]
    rows = []
    for ln in lines[start + 2:]:
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) < 2 or not re.fullmatch(r"\d{6}", parts[0]):
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


def smb_leg(df):
    cols = list(df.columns)
    small = [c for c in cols if c.upper().startswith("SMALL") or c.upper().startswith("ME1")]
    big = [c for c in cols if c.upper().startswith("BIG") or c.upper().startswith("ME2")]
    if len(small) != 3 or len(big) != 3:
        small, big = cols[:3], cols[3:6]
    sub = df[small + big].dropna()
    return sub[small].mean(axis=1) - sub[big].mean(axis=1)


legs = [smb_leg(read_first_block(f)) for f in FILES]
combined = pd.concat(legs, axis=1, join="inner").dropna()
combined = combined.sort_index()
smb = combined.mean(axis=1)

out = pd.DataFrame({"date": smb.index.astype(int), "value": smb.values.round(6)})
out.to_csv("output.csv", index=False)
