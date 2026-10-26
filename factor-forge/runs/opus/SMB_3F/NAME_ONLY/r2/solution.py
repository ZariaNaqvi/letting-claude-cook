import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# locate the value-weighted monthly section
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly section not found")

# header line follows
hdr_idx = start + 1
while hdr_idx < len(lines) and lines[hdr_idx].strip() == "":
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]
cols = header[1:]

rows = []
for line in lines[hdr_idx + 1:]:
    s = line.strip()
    if not s:
        if rows:
            break
        continue
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
    rows.append([int(parts[0])] + vals)

df = pd.DataFrame(rows, columns=["date"] + cols)

def find_col(size_key, bm_key):
    for c in cols:
        cu = c.upper()
        if size_key in cu and bm_key in cu:
            return c
    raise KeyError((size_key, bm_key))

# small portfolios: SMALL/ME1 ; big: BIG/ME2
small = [c for c in cols if ("SMALL" in c.upper() or "ME1" in c.upper())]
big = [c for c in cols if ("BIG" in c.upper() or "ME2" in c.upper())]
if len(small) != 3 or len(big) != 3:
    small = cols[0:3]
    big = cols[3:6]

df["value"] = df[small].mean(axis=1, skipna=False) - df[big].mean(axis=1, skipna=False)
out = df[["date", "value"]].dropna()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(6)
out = out.sort_values("date").drop_duplicates("date")
out.to_csv("output.csv", index=False)
