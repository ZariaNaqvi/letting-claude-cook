import re
import numpy as np
import pandas as pd

FILE = "6_Portfolios_ME_OP_2x3.csv"

with open(FILE, "r", encoding="latin-1") as f:
    lines = f.read().splitlines()

# locate first block: Average Value Weighted Returns -- Monthly
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# header line: next non-empty line
j = start + 1
while lines[j].strip() == "":
    j += 1
header = [h.strip() for h in lines[j].split(",")]
cols = header[1:]

rows = []
k = j + 1
date_re = re.compile(r"^\s*(\d{6})\s*$")
while k < len(lines):
    ln = lines[k]
    parts = [p.strip() for p in ln.split(",")]
    if len(parts) < 2 or not date_re.match(parts[0]):
        break
    rows.append([int(parts[0])] + [float(p) if p != "" else np.nan for p in parts[1:len(cols) + 1]])
    k += 1

df = pd.DataFrame(rows, columns=["date"] + cols)
for c in cols:
    df.loc[df[c].isin([-99.99, -999.0]) | (df[c] <= -99.99), c] = np.nan

def find(name):
    key = name.upper().replace(" ", "")
    for c in cols:
        if c.upper().replace(" ", "") == key:
            return c
    raise KeyError(name)

sh, bh = find("SMALL HiOP"), find("BIG HiOP")
sl, bl = find("SMALL LoOP"), find("BIG LoOP")

df["value"] = 0.5 * (df[sh] + df[bh]) - 0.5 * (df[sl] + df[bl])
out = df[["date", "value"]].dropna()
out = out.drop_duplicates("date").sort_values("date")
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
