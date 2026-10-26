import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_INV_2x3.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the first table: "Average Value Weighted Returns -- Monthly"
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    raise RuntimeError("Could not find the value-weighted monthly table")

# Header line is the next line starting with a comma (column names)
hdr_idx = None
for j in range(start + 1, min(start + 10, len(lines))):
    if lines[j].strip().startswith(","):
        hdr_idx = j
        break
if hdr_idx is None:
    raise RuntimeError("Could not find header line")

header = [h.strip() for h in lines[hdr_idx].split(",")]
cols = header[1:]

rows = []
for line in lines[hdr_idx + 1:]:
    s = line.strip()
    if not s:
        # blank line terminates the block
        if rows:
            break
        continue
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        # Non-monthly row (e.g. a new block title or annual YYYY) ends the block
        break
    vals = parts[1:]
    if len(vals) != len(cols):
        break
    try:
        nums = [float(v) for v in vals]
    except ValueError:
        break
    rows.append([int(parts[0])] + nums)

df = pd.DataFrame(rows, columns=["date"] + cols)

# Treat missing codes as NaN
for c in cols:
    df.loc[df[c].isin([-99.99, -999.0]), c] = np.nan

def find_col(name):
    for c in cols:
        if c.upper().replace(" ", "") == name.upper().replace(" ", ""):
            return c
    raise KeyError(name)

sl = find_col("SMALL LoINV")
bl = find_col("BIG LoINV")
sh = find_col("SMALL HiINV")
bh = find_col("BIG HiINV")

cma = 0.5 * (df[sl] + df[bl]) - 0.5 * (df[sh] + df[bh])

out = pd.DataFrame({"date": df["date"].astype(int), "value": cma.round(6)})
out = out.dropna(subset=["value"])
out.to_csv("output.csv", index=False)
