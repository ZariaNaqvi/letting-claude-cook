import csv
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_ME_OP_2x3.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = f.read().splitlines()

# Locate the first table: value-weighted monthly returns
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# Header line follows (first non-empty line starting with ',')
j = start + 1
while j < len(lines) and lines[j].strip() == "":
    j += 1
header = [h.strip() for h in next(csv.reader([lines[j]]))]
j += 1

rows = []
while j < len(lines):
    line = lines[j]
    if line.strip() == "":
        break
    parts = [p.strip() for p in next(csv.reader([line]))]
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

def find(name):
    for c in df.columns:
        if c.upper().replace(" ", "") == name.upper().replace(" ", ""):
            return c
    raise KeyError(name)

sh, bh = find("SMALL HiOP"), find("BIG HiOP")
sl, bl = find("SMALL LoOP"), find("BIG LoOP")

sub = df[[sh, bh, sl, bl]].copy()
sub = sub.mask((sub <= -99.99) | (sub == -999))
value = 0.5 * (sub[sh] + sub[bh]) - 0.5 * (sub[sl] + sub[bl])

out = pd.DataFrame({"date": df["date"].astype(int), "value": value})
out = out.dropna(subset=["value"])
out = out.drop_duplicates(subset="date").sort_values("date")
out.to_csv("output.csv", index=False)
