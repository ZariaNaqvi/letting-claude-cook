import re
import pandas as pd
import numpy as np

FNAME = "6_Portfolios_ME_INV_2x3.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [ln.rstrip("\r\n") for ln in f]

# Locate the first (value-weighted monthly) block
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# Header line: next non-empty line
h = start + 1
while lines[h].strip() == "":
    h += 1
header = [c.strip() for c in lines[h].split(",")]
cols = header[1:]

rows = []
for ln in lines[h + 1:]:
    s = ln.strip()
    if s == "":
        break
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    vals = []
    for p in parts[1:1 + len(cols)]:
        try:
            vals.append(float(p))
        except ValueError:
            vals.append(np.nan)
    rows.append([int(parts[0])] + vals)

df = pd.DataFrame(rows, columns=["date"] + cols)

def find_col(name):
    target = name.replace(" ", "").upper()
    for c in cols:
        if c.replace(" ", "").upper() == target:
            return c
    raise KeyError(name)

sl = find_col("SMALL LoINV")
sh = find_col("SMALL HiINV")
bl = find_col("BIG LoINV")
bh = find_col("BIG HiINV")

use = df[["date", sl, sh, bl, bh]].copy()
for c in [sl, sh, bl, bh]:
    use.loc[use[c] <= -99.99, c] = np.nan

use["value"] = 0.5 * (use[sl] + use[bl]) - 0.5 * (use[sh] + use[bh])
out = use[["date", "value"]].dropna()
out = out.drop_duplicates("date").sort_values("date")
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
