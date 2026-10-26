import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_ME_Prior_60_13.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = f.read().splitlines()

# Locate the first (value-weighted monthly) block
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns -- Monthly" in line:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# Header line is the next non-empty line
h = start + 1
while lines[h].strip() == "":
    h += 1
header = [c.strip() for c in lines[h].split(",")]
cols = header[1:]

rows = []
j = h + 1
while j < len(lines):
    line = lines[j].strip()
    if line == "":
        if rows:
            break
        j += 1
        continue
    parts = [p.strip() for p in line.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    rows.append(parts)
    j += 1

df = pd.DataFrame(rows, columns=["date"] + cols)
df["date"] = df["date"].astype(int)
for c in cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[(df[c] <= -99.99 + 1e-9) | (df[c] == -999), c] = np.nan

def find_col(name):
    target = name.replace(" ", "").upper()
    for c in cols:
        if c.replace(" ", "").upper() == target:
            return c
    raise KeyError(name)

sl = find_col("SMALL LoPRIOR")
sh = find_col("SMALL HiPRIOR")
bl = find_col("BIG LoPRIOR")
bh = find_col("BIG HiPRIOR")

df["value"] = 0.5 * (df[sl] + df[bl]) - 0.5 * (df[sh] + df[bh])
out = df[["date", "value"]].dropna().sort_values("date")
out = out.drop_duplicates("date")
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
