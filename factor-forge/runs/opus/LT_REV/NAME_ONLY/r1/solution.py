import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_ME_Prior_60_13.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [l.rstrip("\r\n") for l in f]

# locate the value-weighted monthly block
start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break
if start is None:
    raise RuntimeError("Value weighted monthly block not found")

# header line
hdr_idx = start + 1
while hdr_idx < len(lines) and not lines[hdr_idx].strip():
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
            v = float(p)
        except ValueError:
            v = np.nan
        if v <= -99.99 or v == -999:
            v = np.nan
        vals.append(v)
    rows.append([int(parts[0])] + vals)

df = pd.DataFrame(rows, columns=["date"] + cols)

def find(colnames, size_keys, prior_key):
    for c in colnames:
        cu = c.upper().replace(" ", "")
        if any(k in cu for k in size_keys) and prior_key in cu:
            return c
    raise RuntimeError(f"column not found: {size_keys} {prior_key}")

sl = find(cols, ["SMALL", "ME1"], "LOPRIOR")
sh = find(cols, ["SMALL", "ME1"], "HIPRIOR")
bl = find(cols, ["BIG", "ME2"], "LOPRIOR")
bh = find(cols, ["BIG", "ME2"], "HIPRIOR")

df["value"] = 0.5 * (df[sl] + df[bl]) - 0.5 * (df[sh] + df[bh])
out = df[["date", "value"]].dropna().copy()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(2)
out = out.sort_values("date").drop_duplicates("date")
out.to_csv("output.csv", index=False)
