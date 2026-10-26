import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_Prior_12_2.csv"

with open(fname, "r") as f:
    lines = f.read().splitlines()

# Locate the first monthly value-weighted block
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    # fall back: first header line starting with comma
    for i, line in enumerate(lines):
        if line.startswith(","):
            start = i - 1
            break

# Header line follows the block title
header_idx = start + 1
header = [h.strip() for h in lines[header_idx].split(",")]

rows = []
for line in lines[header_idx + 1:]:
    s = line.strip()
    if s == "":
        if rows:
            break
        continue
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    try:
        vals = [float(p) for p in parts[1:]]
    except ValueError:
        break
    rows.append([int(parts[0])] + vals)

cols = ["date"] + header[1:]
df = pd.DataFrame(rows, columns=cols)
df = df.replace([-99.99, -999.0], np.nan)

# Identify columns
def find_col(df, *keys):
    for c in df.columns:
        cu = c.upper().replace(" ", "")
        if all(k in cu for k in keys):
            return c
    return None

small_lo = find_col(df, "SMALL", "LO")
small_hi = find_col(df, "SMALL", "HI")
big_lo = find_col(df, "BIG", "LO")
big_hi = find_col(df, "BIG", "HI")

if None in (small_lo, small_hi, big_lo, big_hi):
    # fallback on positional ordering
    c = list(df.columns[1:])
    small_lo, small_hi, big_lo, big_hi = c[0], c[2], c[3], c[5]

mom = 0.5 * (df[small_hi] + df[big_hi]) - 0.5 * (df[small_lo] + df[big_lo])

out = pd.DataFrame({"date": df["date"].astype(int), "value": mom.round(2)})
out = out.dropna(subset=["value"])
out.to_csv("output.csv", index=False)
