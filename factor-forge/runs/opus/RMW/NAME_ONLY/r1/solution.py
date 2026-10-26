import re
import numpy as np
import pandas as pd

FN = "6_Portfolios_ME_OP_2x3.csv"

with open(FN, "r", encoding="latin-1") as f:
    lines = [l.rstrip("\n").rstrip("\r") for l in f]

# locate value-weighted monthly section
start = None
for i, l in enumerate(lines):
    s = l.strip().lower()
    if "average value weighted returns" in s and "monthly" in s:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly section not found")

# header line follows
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

def find(pats):
    for c in cols:
        cu = c.upper().replace(" ", "")
        if all(p in cu for p in pats):
            return c
    raise RuntimeError(f"column not found: {pats}")

sl = find(["SMALL", "LOOP"])
sh = find(["SMALL", "HIOP"])
bl = find(["BIG", "LOOP"])
bh = find(["BIG", "HIOP"])

df["value"] = 0.5 * (df[sh] + df[bh]) - 0.5 * (df[sl] + df[bl])
out = df[["date", "value"]].dropna()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
