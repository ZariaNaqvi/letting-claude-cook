import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_Prior_1_0.csv"

with open(fname, "r") as f:
    lines = f.readlines()

# Locate the first table: "Average Value Weighted Returns -- Monthly"
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns -- Monthly" in line:
        start = i
        break
if start is None:
    raise RuntimeError("Could not find value-weighted monthly table")

# Header line is the next line starting with a comma
hdr_idx = start + 1
while hdr_idx < len(lines) and not lines[hdr_idx].strip().startswith(","):
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].strip().split(",")]
header[0] = "date"

rows = []
for line in lines[hdr_idx + 1:]:
    s = line.strip()
    if not s:
        break
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    if len(parts) != len(header):
        break
    rows.append(parts)

df = pd.DataFrame(rows, columns=header)
df["date"] = df["date"].astype(int)
for c in header[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Replace missing codes
for c in header[1:]:
    df.loc[df[c].isin([-99.99, -999.0, -999]), c] = np.nan

sl = df["SMALL LoPRIOR"]
bl = df["BIG LoPRIOR"]
sh = df["SMALL HiPRIOR"]
bh = df["BIG HiPRIOR"]

df["value"] = 0.5 * (sl + bl) - 0.5 * (sh + bh)

out = df[["date", "value"]].dropna(subset=["value"]).copy()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
