import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_Prior_12_2.csv"

with open(fname, "r") as f:
    lines = f.read().splitlines()

# Locate the first "Average Value Weighted Returns -- Monthly" section
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    # fallback: first line that looks like a header starting with comma
    for i, line in enumerate(lines):
        if line.startswith(","):
            start = i - 1
            break

# Find header line (starts with ',') after start
hdr = None
for i in range(start, len(lines)):
    if lines[i].strip().startswith(","):
        hdr = i
        break

cols = [c.strip() for c in lines[hdr].split(",")]
cols[0] = "date"

rows = []
pat = re.compile(r"^\s*\d{6}\s*,")
for i in range(hdr + 1, len(lines)):
    line = lines[i]
    if not pat.match(line):
        # end of monthly section (blank line or next header)
        if line.strip() == "" or not re.match(r"^\s*\d", line):
            break
        else:
            break
    parts = [p.strip() for p in line.split(",")]
    if len(parts) != len(cols):
        continue
    rows.append(parts)

df = pd.DataFrame(rows, columns=cols)
df["date"] = df["date"].astype(int)
for c in cols[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Mark missing codes
vals = df[cols[1:]]
vals = vals.mask((vals <= -99.99) | (vals <= -999))
df[cols[1:]] = vals

# Identify columns by name
def find_col(keys):
    for c in cols[1:]:
        cu = c.upper().replace(" ", "")
        if all(k in cu for k in keys):
            return c
    raise KeyError(keys)

small_lo = find_col(["SMALL", "LO"])
small_hi = find_col(["SMALL", "HI"])
big_lo = find_col(["BIG", "LO"])
big_hi = find_col(["BIG", "HI"])

mom = 0.5 * (df[small_hi] + df[big_hi]) - 0.5 * (df[small_lo] + df[big_lo])

out = pd.DataFrame({"date": df["date"], "value": mom.round(2)})
out = out.dropna(subset=["value"])
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
