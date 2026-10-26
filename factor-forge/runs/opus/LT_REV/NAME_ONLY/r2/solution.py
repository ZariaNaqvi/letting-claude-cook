import re
import numpy as np
import pandas as pd

FILE = "6_Portfolios_ME_Prior_60_13.csv"

with open(FILE, "r", encoding="latin-1") as f:
    lines = f.read().splitlines()

# locate the value-weighted monthly section
start = None
for i, ln in enumerate(lines):
    if "Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly section not found")

# header line follows
hdr_idx = start + 1
while not lines[hdr_idx].strip().startswith(","):
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")[1:]]

rows = []
for ln in lines[hdr_idx + 1:]:
    s = ln.strip()
    if not s:
        break
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    rows.append([int(parts[0])] + [float(p) for p in parts[1:1 + len(header)]])

df = pd.DataFrame(rows, columns=["date"] + header)

def find_col(keys):
    for c in header:
        cu = c.upper().replace(" ", "")
        if all(k in cu for k in keys):
            return c
    raise RuntimeError(f"column with {keys} not found")

sl = find_col(["SMALL", "LOPRIOR"])
sh = find_col(["SMALL", "HIPRIOR"])
bl = find_col(["BIG", "LOPRIOR"])
bh = find_col(["BIG", "HIPRIOR"])

vals = df[[sl, sh, bl, bh]].astype(float)
missing = (vals <= -99.99 + 1e-9) | (vals.isna())
mask = ~missing.any(axis=1)

df = df[mask].copy()
df["value"] = 0.5 * (df[sl] + df[bl]) - 0.5 * (df[sh] + df[bh])
df["value"] = df["value"].round(2)

out = df[["date", "value"]].copy()
out["date"] = out["date"].astype(int)
out = out.sort_values("date").drop_duplicates("date")
out.to_csv("output.csv", index=False)
