import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_OP_2x3.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the first "Average Value Weighted Returns -- Monthly" section
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    # fallback: first block of monthly rows (6-digit dates)
    start = 0

# Header line is the next line containing commas after start
j = start + 1
while j < len(lines) and not lines[j].strip().startswith(","):
    j += 1
header = [c.strip() for c in lines[j].split(",")]
j += 1

rows = []
pat = re.compile(r"^\s*(\d{6})\s*,")
while j < len(lines):
    line = lines[j]
    if not line.strip():
        break
    m = pat.match(line)
    if not m:
        break
    parts = [p.strip() for p in line.split(",")]
    date = int(parts[0])
    vals = []
    for p in parts[1:]:
        try:
            vals.append(float(p))
        except ValueError:
            vals.append(np.nan)
    rows.append([date] + vals)
    j += 1

cols = ["date"] + header[1:len(rows[0])]
df = pd.DataFrame(rows, columns=cols)
df = df.replace([-99.99, -999.0], np.nan)

# Identify columns by name (robust to spacing)
def find_col(keys):
    for c in df.columns:
        cn = c.upper().replace(" ", "")
        if all(k in cn for k in keys):
            return c
    raise KeyError(keys)

small_lo = find_col(["SMALL", "LOOP"])
small_hi = find_col(["SMALL", "HIOP"])
big_lo = find_col(["BIG", "LOOP"])
big_hi = find_col(["BIG", "HIOP"])

rmw = 0.5 * (df[small_hi] + df[big_hi]) - 0.5 * (df[small_lo] + df[big_lo])

out = pd.DataFrame({"date": df["date"].astype(int), "value": rmw.round(4)})
out = out.dropna(subset=["value"])
out.to_csv("output.csv", index=False)
