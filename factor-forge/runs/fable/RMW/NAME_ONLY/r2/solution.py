import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_OP_2x3.csv"

with open(fname, "r") as f:
    lines = f.readlines()

# Locate the first block: "Average Value Weighted Returns -- Monthly"
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    # fallback: first header line with column names
    for i, line in enumerate(lines):
        if line.strip().startswith(",") and "LoOP" in line:
            start = i - 1
            break

# Find header line (starts with comma) after start
hdr = None
for i in range(start, len(lines)):
    if lines[i].strip().startswith(","):
        hdr = i
        break

cols = [c.strip() for c in lines[hdr].strip().split(",")]
cols[0] = "date"

rows = []
for i in range(hdr + 1, len(lines)):
    s = lines[i].strip()
    if s == "":
        break
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    rows.append(parts)

df = pd.DataFrame(rows, columns=cols)
df["date"] = df["date"].astype(int)
for c in cols[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Identify columns by position: SMALL LoOP, ME1 OP2, SMALL HiOP, BIG LoOP, ME2 OP2, BIG HiOP
c = cols
small_lo, small_hi = df[c[1]], df[c[3]]
big_lo, big_hi = df[c[4]], df[c[6]]

# Treat missing codes as NaN
mask = pd.DataFrame({"a": small_lo, "b": small_hi, "c": big_lo, "d": big_hi})
mask = mask.replace([-99.99, -999.0, -999], np.nan)

rmw = 0.5 * (mask["b"] + mask["d"]) - 0.5 * (mask["a"] + mask["c"])

out = pd.DataFrame({"date": df["date"], "value": rmw})
out = out.dropna(subset=["value"])
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
