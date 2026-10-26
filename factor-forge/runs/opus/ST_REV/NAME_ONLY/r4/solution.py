import re
import numpy as np
import pandas as pd

FN = "6_Portfolios_ME_Prior_1_0.csv"

with open(FN, "r", encoding="latin-1") as f:
    lines = [l.rstrip("\r\n") for l in f]

# locate the first monthly value-weighted block
start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break
if start is None:
    raise RuntimeError("Monthly VW block not found")

# header line follows
hdr_idx = start + 1
while not lines[hdr_idx].strip():
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]
cols = header[1:]

rows = []
for l in lines[hdr_idx + 1:]:
    parts = [p.strip() for p in l.split(",")]
    if not parts or not re.fullmatch(r"\d{6}", parts[0]):
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

def find(pattern):
    for c in cols:
        if re.fullmatch(pattern, c.upper().replace("  ", " ")):
            return c
    raise RuntimeError(f"column {pattern} not found in {cols}")

sl = find(r"SMALL\s*LOPRIOR")
sh = find(r"SMALL\s*HIPRIOR")
bl = find(r"BIG\s*LOPRIOR")
bh = find(r"BIG\s*HIPRIOR")

df["value"] = 0.5 * (df[sl] + df[bl]) - 0.5 * (df[sh] + df[bh])
out = df[["date", "value"]].dropna()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
