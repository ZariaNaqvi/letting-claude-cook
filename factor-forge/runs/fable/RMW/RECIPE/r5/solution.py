import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_OP_2x3.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

# Locate the first "Average Value Weighted Returns -- Monthly" block
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    raise RuntimeError("Could not find monthly value-weighted block")

# Header line is the next line starting with a comma
hdr_idx = start + 1
while hdr_idx < len(lines) and not lines[hdr_idx].strip().startswith(","):
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].strip().split(",")]

rows = []
for line in lines[hdr_idx + 1:]:
    s = line.strip()
    if not s:
        # blank line ends the block (only if we've gathered data)
        if rows:
            break
        continue
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    rows.append(parts)

df = pd.DataFrame(rows, columns=header)
df.rename(columns={header[0]: "date"}, inplace=True)
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Treat missing codes as NaN
for c in df.columns[1:]:
    df.loc[df[c] <= -99.99, c] = np.nan

cols = {c.upper().replace(" ", ""): c for c in df.columns[1:]}
def get(name):
    key = name.upper().replace(" ", "")
    return df[cols[key]]

small_hi = get("SMALL HiOP")
big_hi = get("BIG HiOP")
small_lo = get("SMALL LoOP")
big_lo = get("BIG LoOP")

rmw = 0.5 * (small_hi + big_hi) - 0.5 * (small_lo + big_lo)

out = pd.DataFrame({"date": df["date"].astype(int), "value": rmw})
out = out.dropna(subset=["value"])
out.to_csv("output.csv", index=False)
