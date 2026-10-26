import pandas as pd
import numpy as np

FNAME = "6_Portfolios_ME_OP_2x3.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [l.rstrip("\n").rstrip("\r") for l in f]

# locate the monthly value-weighted block
start = None
for i, l in enumerate(lines):
    s = l.strip().lower()
    if "average value weighted returns" in s and "monthly" in s:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly section not found")

# header line
hdr_idx = start + 1
while lines[hdr_idx].strip() == "":
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]
cols = header[1:]

rows = []
for l in lines[hdr_idx + 1:]:
    s = l.strip()
    if s == "":
        break
    parts = [p.strip() for p in s.split(",")]
    tok = parts[0]
    if not (tok.isdigit() and len(tok) == 6):
        break
    vals = []
    for p in parts[1:1 + len(cols)]:
        try:
            vals.append(float(p))
        except ValueError:
            vals.append(np.nan)
    rows.append([int(tok)] + vals)

df = pd.DataFrame(rows, columns=["date"] + cols)
for c in cols:
    df.loc[df[c] <= -99.99, c] = np.nan

def find(pred):
    for c in cols:
        u = c.upper().replace(" ", "")
        if pred(u):
            return c
    raise RuntimeError("column not found")

small_lo = find(lambda u: ("SMALL" in u or "ME1" in u) and "LO" in u)
small_hi = find(lambda u: ("SMALL" in u or "ME1" in u) and "HI" in u)
big_lo = find(lambda u: ("BIG" in u or "ME2" in u) and "LO" in u)
big_hi = find(lambda u: ("BIG" in u or "ME2" in u) and "HI" in u)

df["value"] = 0.5 * (df[small_hi] + df[big_hi]) - 0.5 * (df[small_lo] + df[big_lo])
out = df[["date", "value"]].dropna()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
