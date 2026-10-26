import csv
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the monthly value-weighted section
start = None
for i, ln in enumerate(lines):
    s = ln.strip().lower()
    if "value weighted returns" in s and "monthly" in s:
        start = i
        break
if start is None:
    raise RuntimeError("Monthly value-weighted section not found")

# Header line
hdr_idx = start + 1
while lines[hdr_idx].strip() == "":
    hdr_idx += 1
header = [h.strip() for h in next(csv.reader([lines[hdr_idx]]))]
cols = header[1:]

rows = []
for ln in lines[hdr_idx + 1:]:
    if ln.strip() == "":
        break
    parts = [p.strip() for p in next(csv.reader([ln]))]
    d = parts[0]
    if not (d.isdigit() and len(d) == 6):
        break
    vals = []
    for p in parts[1:1 + len(cols)]:
        try:
            vals.append(float(p))
        except ValueError:
            vals.append(np.nan)
    rows.append([int(d)] + vals)

df = pd.DataFrame(rows, columns=["date"] + cols)
for c in cols:
    df.loc[df[c] <= -99.99 + 1e-9, c] = np.nan


def find_col(keys):
    for c in cols:
        u = c.upper().replace(" ", "")
        if all(k in u for k in keys):
            return c
    raise RuntimeError(f"column not found for {keys}")


# Expected names: SMALL LoBM, ME1 BM2, SMALL HiBM, BIG LoBM, ME2 BM2, BIG HiBM
try:
    sl = find_col(["SMALL", "LOBM"])
    sh = find_col(["SMALL", "HIBM"])
    bl = find_col(["BIG", "LOBM"])
    bh = find_col(["BIG", "HIBM"])
except RuntimeError:
    sl, _, sh, bl, _, bh = cols[:6]

hml = 0.5 * (df[sh] + df[bh]) - 0.5 * (df[sl] + df[bl])
out = pd.DataFrame({"date": df["date"].astype(int), "value": hml})
out = out.dropna().sort_values("date").drop_duplicates("date")
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
