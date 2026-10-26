import re
import pandas as pd
import numpy as np

FNAME = "6_Portfolios_ME_Prior_1_0.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [ln.rstrip("\r\n") for ln in f]

# Locate the first block: Average Value Weighted Returns -- Monthly
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns" in ln and "Monthly" in ln:
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
    ln = lines[j]
    parts = [p.strip() for p in ln.split(",")]
    if len(parts) < 2 or not re.fullmatch(r"\d{6}", parts[0]):
        break
    rows.append(parts[: len(header)])
    j += 1

df = pd.DataFrame(rows, columns=["date"] + cols)
df["date"] = df["date"].astype(int)
for c in cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

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

sub = df[["date", sl, sh, bl, bh]].copy()
for c in [sl, sh, bl, bh]:
    sub.loc[(sub[c] <= -99.99) | (sub[c] == -999), c] = np.nan
sub = sub.dropna()

sub["value"] = 0.5 * (sub[sl] + sub[bl]) - 0.5 * (sub[sh] + sub[bh])
out = sub[["date", "value"]].sort_values("date").drop_duplicates("date")
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
