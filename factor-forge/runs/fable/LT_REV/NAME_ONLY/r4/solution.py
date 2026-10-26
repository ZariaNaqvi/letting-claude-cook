import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_Prior_60_13.csv"

with open(fname, "r") as f:
    lines = f.read().splitlines()

# Locate the first section: "Average Value Weighted Returns -- Monthly"
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    # fallback: first header line starting with a comma
    for i, line in enumerate(lines):
        if line.startswith(",") and "PRIOR" in line.upper():
            start = i - 1
            break

# Find the header (column names) line after the section title
hdr_idx = start + 1
while hdr_idx < len(lines) and not lines[hdr_idx].strip().startswith(","):
    hdr_idx += 1
header = [c.strip() for c in lines[hdr_idx].split(",")]

rows = []
pat = re.compile(r"^\s*(\d{6})\s*,")
for line in lines[hdr_idx + 1:]:
    if not line.strip():
        break  # end of monthly section
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

cols = ["date"] + header[1:len(rows[0])]
df = pd.DataFrame(rows, columns=cols)

# Mark missing values
for c in cols[1:]:
    df.loc[df[c] <= -99.0, c] = np.nan

# Identify columns by name
def find_col(keys):
    for c in cols[1:]:
        cu = c.upper()
        if all(k in cu for k in keys):
            return c
    raise KeyError(keys)

small_lo = find_col(["SMALL", "LO"])
small_hi = find_col(["SMALL", "HI"])
big_lo = find_col(["BIG", "LO"])
big_hi = find_col(["BIG", "HI"])

# LT_Rev = 1/2 (Small Low + Big Low) - 1/2 (Small High + Big High)
df["value"] = 0.5 * (df[small_lo] + df[big_lo]) - 0.5 * (df[small_hi] + df[big_hi])

out = df[["date", "value"]].dropna().copy()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(2)
out.to_csv("output.csv", index=False)
