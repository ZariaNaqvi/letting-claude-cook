import re
import numpy as np
import pandas as pd

FILE = "6_Portfolios_ME_INV_2x3.csv"

with open(FILE, "r", encoding="latin-1") as f:
    lines = [l.rstrip("\n").rstrip("\r") for l in f]

# locate the monthly value-weighted block
start = None
for i, l in enumerate(lines):
    if "Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break
if start is None:
    raise RuntimeError("Monthly value-weighted block not found")

# header line
hdr_idx = start + 1
while lines[hdr_idx].strip() == "":
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]
cols = header[1:]

rows = []
for l in lines[hdr_idx + 1:]:
    s = l.strip()
    if not s:
        break
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    vals = []
    for p in parts[1:1 + len(cols)]:
        try:
            vals.append(float(p))
        except ValueError:
            vals.append(np.nan)
    rows.append([int(parts[0])] + vals)

df = pd.DataFrame(rows, columns=["date"] + cols)
for c in cols:
    df.loc[df[c] <= -99.99, c] = np.nan

def find_col(size_keys, inv_key):
    for c in cols:
        cu = c.upper().replace(" ", "")
        if any(k in cu for k in size_keys) and inv_key in cu:
            return c
    raise RuntimeError(f"column not found {size_keys} {inv_key}")

# Column order per Ken French: SMALL LoINV, ME1 INV2, SMALL HiINV, BIG LoINV, ME2 INV2, BIG HiINV
try:
    sl = find_col(["SMALL", "ME1"], "LOINV")
    sh = find_col(["SMALL", "ME1"], "HIINV")
    bl = find_col(["BIG", "ME2"], "LOINV")
    bh = find_col(["BIG", "ME2"], "HIINV")
except RuntimeError:
    sl, _, sh, bl, _, bh = cols[:6]

df["value"] = 0.5 * (df[sl] + df[bl]) - 0.5 * (df[sh] + df[bh])
out = df[["date", "value"]].dropna()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
