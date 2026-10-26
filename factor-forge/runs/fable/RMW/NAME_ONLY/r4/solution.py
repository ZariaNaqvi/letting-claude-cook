import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_OP_2x3.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the first monthly value-weighted section
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    # fallback: first header line starting with comma
    for i, line in enumerate(lines):
        if line.strip().startswith(","):
            start = i - 1
            break

# Find header line (starts with comma) after start
hdr = None
for j in range(start, len(lines)):
    if lines[j].strip().startswith(","):
        hdr = j
        break

cols = [c.strip() for c in lines[hdr].split(",")]
rows = []
for k in range(hdr + 1, len(lines)):
    line = lines[k].strip()
    if not line:
        if rows:
            break
        continue
    parts = [p.strip() for p in line.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        if rows:
            break
        continue
    try:
        vals = [float(x) for x in parts[1:]]
    except ValueError:
        break
    rows.append([int(parts[0])] + vals)

df = pd.DataFrame(rows, columns=cols)
df = df.rename(columns={cols[0]: "date"})
df = df.set_index("date")

# Replace missing codes
df = df.replace([-99.99, -999, -999.0], np.nan)

# Identify columns by name
names = list(df.columns)
def find(pred):
    for n in names:
        if pred(n.upper().replace(" ", "")):
            return n
    raise KeyError
small_lo = find(lambda n: "SMALL" in n and "LOOP" in n)
small_hi = find(lambda n: "SMALL" in n and "HIOP" in n)
big_lo = find(lambda n: "BIG" in n and "LOOP" in n)
big_hi = find(lambda n: "BIG" in n and "HIOP" in n)

rmw = 0.5 * (df[small_hi] + df[big_hi]) - 0.5 * (df[small_lo] + df[big_lo])

out = pd.DataFrame({"date": df.index.astype(int), "value": rmw.values})
out = out.dropna(subset=["value"])
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
