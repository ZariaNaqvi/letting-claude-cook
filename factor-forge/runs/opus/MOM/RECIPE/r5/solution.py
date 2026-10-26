import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_ME_Prior_12_2.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [l.rstrip("\r\n") for l in f]

# Locate the first block: Average Value Weighted Returns -- Monthly
start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# Header line follows
hdr_idx = start + 1
while lines[hdr_idx].strip() == "":
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]
cols = header[1:]

rows = []
for l in lines[hdr_idx + 1:]:
    s = l.strip()
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
    while len(vals) < len(cols):
        vals.append(np.nan)
    rows.append([int(parts[0])] + vals)

df = pd.DataFrame(rows, columns=["date"] + cols)

def find_col(name):
    target = name.upper().replace(" ", "")
    for c in cols:
        if c.upper().replace(" ", "") == target:
            return c
    raise KeyError(name)

sh = find_col("SMALL HiPRIOR")
bh = find_col("BIG HiPRIOR")
sl = find_col("SMALL LoPRIOR")
bl = find_col("BIG LoPRIOR")

sub = df[["date", sh, bh, sl, bl]].copy()
for c in [sh, bh, sl, bl]:
    sub[c] = pd.to_numeric(sub[c], errors="coerce")
    sub.loc[(sub[c] <= -99.99) | (sub[c] <= -999), c] = np.nan

sub["value"] = 0.5 * (sub[sh] + sub[bh]) - 0.5 * (sub[sl] + sub[bl])
out = sub[["date", "value"]].dropna()
out = out.drop_duplicates("date").sort_values("date")
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
