import re
import numpy as np
import pandas as pd

FN = "6_Portfolios_ME_OP_2x3.csv"

with open(FN, "r", encoding="latin-1") as f:
    lines = [l.rstrip("\r\n") for l in f]

start = None
for i, l in enumerate(lines):
    s = l.strip().lower()
    if "average value weighted returns" in s and "monthly" in s:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly section not found")

# header line
h = start + 1
while lines[h].strip() == "":
    h += 1
header = [c.strip() for c in lines[h].split(",")]

rows = []
for l in lines[h + 1:]:
    s = l.strip()
    if s == "":
        break
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    rows.append(parts)

cols = ["date"] + header[1:]
df = pd.DataFrame(rows, columns=cols[:len(rows[0])])
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c] <= -99.99, c] = np.nan

def find(pattern):
    for c in df.columns[1:]:
        if re.fullmatch(pattern, c.replace(" ", "").upper()):
            return c
    raise RuntimeError(f"column {pattern} not found")

# columns: SMALL LoOP, ME1 OP2, SMALL HiOP, BIG LoOP, ME2 OP2, BIG HiOP
c = list(df.columns[1:])
sw, sr, bw, br = c[0], c[2], c[3], c[5]
try:
    sw = find(r"SMALLLOOP"); sr = find(r"SMALLHIOP")
    bw = find(r"BIGLOOP"); br = find(r"BIGHIOP")
except RuntimeError:
    pass

val = 0.5 * (df[sr] + df[br]) - 0.5 * (df[sw] + df[bw])
out = pd.DataFrame({"date": df["date"], "value": val}).dropna()
out = out.sort_values("date").drop_duplicates("date")
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
