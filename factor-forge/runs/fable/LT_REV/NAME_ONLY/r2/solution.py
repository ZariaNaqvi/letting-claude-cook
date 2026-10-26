import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_Prior_60_13.csv"

with open(fname, "r") as f:
    lines = f.read().splitlines()

# Locate the first monthly value-weighted section
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns -- Monthly" in line:
        start = i
        break
if start is None:
    # fallback: first line that starts with comma (header of first table)
    for i, line in enumerate(lines):
        if line.startswith(","):
            start = i - 1
            break

# Header line follows the section title
hdr_idx = start + 1
while hdr_idx < len(lines) and not lines[hdr_idx].strip().startswith(","):
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]

rows = []
pat = re.compile(r"^\s*(\d{6})\s*,")
for line in lines[hdr_idx + 1:]:
    m = pat.match(line)
    if not m:
        if line.strip() == "" and not rows:
            continue
        break
    parts = [p.strip() for p in line.split(",")]
    rows.append(parts)

df = pd.DataFrame(rows, columns=header[:len(rows[0])])
df = df.rename(columns={df.columns[0]: "date"})
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Identify columns
cols = list(df.columns[1:])
def find(sub):
    for c in cols:
        if sub.lower() in c.lower():
            return c
    raise KeyError(sub)

small_lo = find("SMALL LoPRIOR")
small_hi = find("SMALL HiPRIOR")
big_lo = find("BIG LoPRIOR")
big_hi = find("BIG HiPRIOR")

# Treat missing codes as NaN
for c in [small_lo, small_hi, big_lo, big_hi]:
    df.loc[df[c] <= -99.0, c] = np.nan

# LT_Rev = 1/2 (Small Low + Big Low) - 1/2 (Small High + Big High)
df["value"] = 0.5 * (df[small_lo] + df[big_lo]) - 0.5 * (df[small_hi] + df[big_hi])

out = df[["date", "value"]].dropna()
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
