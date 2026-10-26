import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_ME_Prior_12_2.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = f.read().splitlines()

# locate the monthly value-weighted section
start = None
for i, ln in enumerate(lines):
    s = ln.strip().lower()
    if "value weighted returns" in s and "monthly" in s:
        start = i
        break
if start is None:
    raise RuntimeError("Monthly VW section not found")

# header line
hdr_idx = start + 1
while not lines[hdr_idx].strip():
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")][1:]

rows = []
for ln in lines[hdr_idx + 1:]:
    s = ln.strip()
    if not s:
        if rows:
            break
        continue
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    try:
        vals = [float(p) for p in parts[1:1 + len(header)]]
    except ValueError:
        continue
    rows.append([int(parts[0])] + vals)

df = pd.DataFrame(rows, columns=["date"] + header)

def find_col(size_keys, prior_key):
    for c in header:
        cu = c.upper().replace(" ", "")
        if any(k in cu for k in size_keys) and prior_key in cu:
            return c
    raise RuntimeError(f"column not found: {size_keys} {prior_key}")

sl = find_col(["SMALL", "ME1"], "LOPRIOR")
sh = find_col(["SMALL", "ME1"], "HIPRIOR")
bl = find_col(["BIG", "ME2"], "LOPRIOR")
bh = find_col(["BIG", "ME2"], "HIPRIOR")

for c in [sl, sh, bl, bh]:
    df.loc[(df[c] <= -99.99) | (df[c] <= -999), c] = np.nan

df["value"] = 0.5 * (df[sh] + df[bh]) - 0.5 * (df[sl] + df[bl])
out = df[["date", "value"]].dropna()
out["value"] = out["value"].round(4)
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
