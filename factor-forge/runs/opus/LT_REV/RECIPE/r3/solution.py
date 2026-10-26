import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_ME_Prior_60_13.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = f.read().splitlines()

# Locate the first block: Average Value Weighted Returns -- Monthly
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# Header line is the next non-empty line
j = start + 1
while j < len(lines) and lines[j].strip() == "":
    j += 1
header = [h.strip() for h in lines[j].split(",")]
cols = header[1:]

rows = []
k = j + 1
date_re = re.compile(r"^\s*(\d{6})\s*,")
while k < len(lines):
    ln = lines[k]
    m = date_re.match(ln)
    if not m:
        break
    parts = [p.strip() for p in ln.split(",")]
    date = int(parts[0])
    vals = []
    for p in parts[1:1 + len(cols)]:
        try:
            v = float(p)
        except ValueError:
            v = np.nan
        vals.append(v)
    while len(vals) < len(cols):
        vals.append(np.nan)
    rows.append([date] + vals)
    k += 1

df = pd.DataFrame(rows, columns=["date"] + cols)
for c in cols:
    df.loc[(df[c] <= -99.99) | (df[c] == -999), c] = np.nan

def find_col(name):
    norm = lambda s: re.sub(r"\s+", " ", s.strip().upper())
    for c in cols:
        if norm(c) == norm(name):
            return c
    raise KeyError(name)

sl = find_col("SMALL LoPRIOR")
sh = find_col("SMALL HiPRIOR")
bl = find_col("BIG LoPRIOR")
bh = find_col("BIG HiPRIOR")

df["value"] = 0.5 * (df[sl] + df[bl]) - 0.5 * (df[sh] + df[bh])
out = df[["date", "value"]].dropna()
out = out.drop_duplicates("date").sort_values("date")
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
