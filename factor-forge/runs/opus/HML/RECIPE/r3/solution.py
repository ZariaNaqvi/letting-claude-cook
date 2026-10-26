import csv
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the first block: Average Value Weighted Returns -- Monthly
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# Header line follows
hdr_idx = start + 1
while not lines[hdr_idx].strip():
    hdr_idx += 1
header = [h.strip() for h in next(csv.reader([lines[hdr_idx]]))]
cols = header[1:]

rows = []
for ln in lines[hdr_idx + 1:]:
    s = ln.strip()
    if not s:
        break
    parts = [p.strip() for p in next(csv.reader([s]))]
    d = parts[0]
    if not (d.isdigit() and len(d) == 6):
        break
    vals = []
    for p in parts[1:len(cols) + 1]:
        try:
            vals.append(float(p))
        except ValueError:
            vals.append(np.nan)
    while len(vals) < len(cols):
        vals.append(np.nan)
    rows.append([int(d)] + vals)

df = pd.DataFrame(rows, columns=["date"] + cols)
for c in cols:
    df.loc[df[c] <= -99.99, c] = np.nan

def col(name):
    for c in cols:
        if c.replace(" ", "").upper() == name.replace(" ", "").upper():
            return df[c]
    raise KeyError(name)

sh = col("SMALL HiBM")
bh = col("BIG HiBM")
sl = col("SMALL LoBM")
bl = col("BIG LoBM")

df["value"] = 0.5 * (sh + bh) - 0.5 * (sl + bl)
out = df[["date", "value"]].dropna().copy()
out["date"] = out["date"].astype(int)
out = out.sort_values("date").drop_duplicates("date")
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
