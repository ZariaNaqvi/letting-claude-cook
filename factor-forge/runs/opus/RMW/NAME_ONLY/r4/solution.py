import re
import pandas as pd
import numpy as np

FNAME = "6_Portfolios_ME_OP_2x3.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = [l.rstrip("\r\n") for l in f]

# locate value-weighted monthly section
start = None
for i, l in enumerate(lines):
    s = l.strip().lower()
    if "average value weighted returns" in s and "monthly" in s:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly section not found")

# header line: next non-empty line
j = start + 1
while j < len(lines) and lines[j].strip() == "":
    j += 1
header = [h.strip() for h in lines[j].split(",")]
j += 1

rows = []
while j < len(lines):
    l = lines[j].strip()
    if not l:
        break
    parts = [p.strip() for p in l.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    rows.append(parts)
    j += 1

cols = ["date"] + header[1:]
df = pd.DataFrame([r[:len(cols)] for r in rows], columns=cols)
df["date"] = df["date"].astype(int)
for c in cols[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

def find_col(keys):
    for c in cols[1:]:
        u = c.upper().replace(" ", "")
        if all(k in u for k in keys):
            return c
    raise RuntimeError(f"column not found: {keys}")

s_lo = find_col(["SMALL", "LOOP"])
s_hi = find_col(["SMALL", "HIOP"])
b_lo = find_col(["BIG", "LOOP"])
b_hi = find_col(["BIG", "HIOP"])

use = df[["date", s_lo, s_hi, b_lo, b_hi]].copy()
for c in [s_lo, s_hi, b_lo, b_hi]:
    use.loc[(use[c] <= -99.99) | (use[c] == -999), c] = np.nan
use = use.dropna()

use["value"] = 0.5 * (use[s_hi] + use[b_hi]) - 0.5 * (use[s_lo] + use[b_lo])
out = use[["date", "value"]].sort_values("date").drop_duplicates("date")
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
