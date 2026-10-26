import pandas as pd
import numpy as np

FNAME = "6_Portfolios_ME_INV_2x3.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [l.rstrip("\n").rstrip("\r") for l in f]

# locate the value-weighted monthly section
start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly section not found")

header = [h.strip() for h in lines[start + 1].split(",")]
rows = []
for l in lines[start + 2:]:
    s = l.strip()
    if not s:
        break
    parts = [p.strip() for p in s.split(",")]
    tok = parts[0]
    if not (tok.isdigit() and len(tok) == 6):
        break
    vals = []
    for p in parts[1:]:
        try:
            vals.append(float(p))
        except ValueError:
            vals.append(np.nan)
    rows.append([int(tok)] + vals)

cols = ["date"] + header[1:]
df = pd.DataFrame(rows, columns=cols[: len(rows[0])])
num = df.columns[1:]
df[num] = df[num].astype(float)
df[num] = df[num].mask(df[num] <= -99.99)

def find(colnames, *keys):
    for c in colnames:
        cu = c.upper().replace(" ", "")
        if all(k in cu for k in keys):
            return c
    raise KeyError(keys)

c = list(num)
# Order in file: SMALL LoINV, ME1 INV2, SMALL HiINV, BIG LoINV, ME2 INV2, BIG HiINV
try:
    sl = find(c, "SMALL", "LOINV")
    sh = find(c, "SMALL", "HIINV")
    bl = find(c, "BIG", "LOINV")
    bh = find(c, "BIG", "HIINV")
except KeyError:
    sl, sh, bl, bh = c[0], c[2], c[3], c[5]

cma = 0.5 * (df[sl] + df[bl]) - 0.5 * (df[sh] + df[bh])
out = pd.DataFrame({"date": df["date"].astype(int), "value": cma})
out = out.dropna().sort_values("date").drop_duplicates("date")
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
