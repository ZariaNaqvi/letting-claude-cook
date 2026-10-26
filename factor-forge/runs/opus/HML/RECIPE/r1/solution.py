import re
import pandas as pd
import numpy as np

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [ln.rstrip("\r\n") for ln in f]

# locate first block: Average Value Weighted Returns -- Monthly
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# header line
h = start + 1
while lines[h].strip() == "":
    h += 1
header = [c.strip() for c in lines[h].split(",")]
cols = header[1:]

rows = []
j = h + 1
date_re = re.compile(r"^\s*(\d{6})\s*$")
while j < len(lines):
    ln = lines[j]
    parts = [p.strip() for p in ln.split(",")]
    if len(parts) < 2 or not date_re.match(parts[0]):
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
    j += 1

df = pd.DataFrame(rows, columns=["date"] + cols)
for c in cols:
    df.loc[df[c] <= -99.99, c] = np.nan

def find(name):
    key = name.replace(" ", "").upper()
    for c in cols:
        if c.replace(" ", "").upper() == key:
            return c
    raise KeyError(name)

sh, bh = find("SMALL HiBM"), find("BIG HiBM")
sl, bl = find("SMALL LoBM"), find("BIG LoBM")

df["value"] = 0.5 * (df[sh] + df[bh]) - 0.5 * (df[sl] + df[bl])
out = df[["date", "value"]].dropna()
out = out.drop_duplicates("date").sort_values("date")
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
