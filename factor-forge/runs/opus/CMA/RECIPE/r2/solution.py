import csv
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_ME_INV_2x3.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate first block: 'Average Value Weighted Returns -- Monthly'
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Could not find value-weighted monthly block")

# Header line is the next non-empty line
j = start + 1
while j < len(lines) and lines[j].strip() == "":
    j += 1
header = [h.strip() for h in next(csv.reader([lines[j]]))]
j += 1

rows = []
while j < len(lines):
    ln = lines[j]
    if ln.strip() == "":
        break
    parts = [p.strip() for p in next(csv.reader([ln]))]
    d = parts[0]
    if not (d.isdigit() and len(d) == 6):
        break
    rows.append(parts)
    j += 1

cols = ["date"] + header[1:]
df = pd.DataFrame([r[:len(cols)] for r in rows], columns=cols)
df["date"] = df["date"].astype(int)
for c in cols[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c] <= -99.99, c] = np.nan

def find(name):
    for c in cols[1:]:
        if c.replace(" ", "").upper() == name.replace(" ", "").upper():
            return c
    raise KeyError(name)

sl, sh = find("SMALL LoINV"), find("SMALL HiINV")
bl, bh = find("BIG LoINV"), find("BIG HiINV")

df["value"] = 0.5 * (df[sl] + df[bl]) - 0.5 * (df[sh] + df[bh])
out = df[["date", "value"]].dropna().sort_values("date")
out = out.drop_duplicates("date")
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
