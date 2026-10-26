import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_Prior_60_13.csv"

with open(fname, "r", encoding="latin-1") as f:
    lines = f.readlines()

# Locate the first table: header line starting with a comma, followed by YYYYMM rows
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns -- Monthly" in line:
        start = i
        break
if start is None:
    # fallback: first line starting with a comma (header)
    for i, line in enumerate(lines):
        if line.startswith(","):
            start = i - 1
            break

# header is the next line that starts with a comma
hdr_idx = start + 1
while hdr_idx < len(lines) and not lines[hdr_idx].strip().startswith(","):
    hdr_idx += 1
header = [c.strip() for c in lines[hdr_idx].strip().split(",")]

rows = []
for line in lines[hdr_idx + 1:]:
    s = line.strip()
    if not s:
        break
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    rows.append(parts)

df = pd.DataFrame(rows, columns=header)
df = df.rename(columns={header[0]: "date"})
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Replace missing indicators
for c in df.columns[1:]:
    df.loc[df[c].isin([-99.99, -999, -999.0]), c] = np.nan

sl = df["SMALL LoPRIOR"]
bl = df["BIG LoPRIOR"]
sh = df["SMALL HiPRIOR"]
bh = df["BIG HiPRIOR"]

df["value"] = 0.5 * (sl + bl) - 0.5 * (sh + bh)

out = df[["date", "value"]].dropna()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
