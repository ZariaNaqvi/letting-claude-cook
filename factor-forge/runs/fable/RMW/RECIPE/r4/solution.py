import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_OP_2x3.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

# Locate the first block: 'Average Value Weighted Returns -- Monthly'
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    raise RuntimeError("Could not find value-weighted monthly block")

# Header line is the next line starting with a comma (column names)
hdr_idx = None
for j in range(start + 1, min(start + 10, len(lines))):
    if lines[j].strip().startswith(","):
        hdr_idx = j
        break
if hdr_idx is None:
    raise RuntimeError("Could not find header line")

header = [c.strip() for c in lines[hdr_idx].strip().split(",")]
header[0] = "date"

rows = []
for j in range(hdr_idx + 1, len(lines)):
    s = lines[j].strip()
    if not s:
        break
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    rows.append(parts)

df = pd.DataFrame(rows, columns=header[:len(rows[0])])
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Treat missing codes as NaN
df = df.replace({-99.99: np.nan, -999.0: np.nan})

def find_col(cols, *keys):
    for c in cols:
        cl = c.upper().replace(" ", "")
        if all(k.upper().replace(" ", "") in cl for k in keys):
            return c
    raise KeyError(keys)

cols = list(df.columns[1:])
s_lo = find_col(cols, "SMALL", "LoOP")
s_hi = find_col(cols, "SMALL", "HiOP")
b_lo = find_col(cols, "BIG", "LoOP")
b_hi = find_col(cols, "BIG", "HiOP")

value = 0.5 * (df[s_hi] + df[b_hi]) - 0.5 * (df[s_lo] + df[b_lo])

out = pd.DataFrame({"date": df["date"].astype(int), "value": value})
out = out.dropna(subset=["value"])
out.to_csv("output.csv", index=False)
