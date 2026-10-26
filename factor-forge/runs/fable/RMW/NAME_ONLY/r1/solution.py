import re
import pandas as pd
import numpy as np

fname = "6_Portfolios_ME_OP_2x3.csv"

with open(fname, "r") as f:
    lines = f.read().splitlines()

# Locate the first "Average Value Weighted Returns -- Monthly" section
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    raise RuntimeError("Could not find monthly value-weighted section")

# Header line follows
header_idx = start + 1
while header_idx < len(lines) and not lines[header_idx].strip().startswith(","):
    header_idx += 1
header = [h.strip() for h in lines[header_idx].split(",")]

rows = []
for line in lines[header_idx + 1:]:
    s = line.strip()
    if not s:
        if rows:
            break
        continue
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    rows.append(parts)

df = pd.DataFrame(rows, columns=header[:len(rows[0])])
df = df.rename(columns={df.columns[0]: "date"})
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c] <= -99, c] = np.nan

# Identify columns: order is SMALL LoOP, ME1 OP2, SMALL HiOP, BIG LoOP, ME2 OP2, BIG HiOP
cols = list(df.columns[1:])
small_lo, small_mid, small_hi, big_lo, big_mid, big_hi = cols[:6]

rmw = 0.5 * (df[small_hi] + df[big_hi]) - 0.5 * (df[small_lo] + df[big_lo])

out = pd.DataFrame({"date": df["date"], "value": rmw.round(4)})
out = out.dropna(subset=["value"])
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
