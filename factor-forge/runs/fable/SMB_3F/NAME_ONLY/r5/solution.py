import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_2x3.csv"

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

# Header line is the next line beginning with a comma
hdr_idx = start + 1
while hdr_idx < len(lines) and not lines[hdr_idx].startswith(","):
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]
colnames = ["date"] + header[1:]

rows = []
date_re = re.compile(r"^\s*\d{6}\s*$")
for line in lines[hdr_idx + 1:]:
    if not line.strip():
        break
    parts = [p.strip() for p in line.split(",")]
    if not date_re.match(parts[0]):
        break
    rows.append(parts)

df = pd.DataFrame(rows, columns=colnames[:len(rows[0])])
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c] <= -99.0, c] = np.nan

small = ["SMALL LoBM", "ME1 BM2", "SMALL HiBM"]
big = ["BIG LoBM", "ME2 BM2", "BIG HiBM"]

smb = (df[small].sum(axis=1) / 3.0) - (df[big].sum(axis=1) / 3.0)

out = pd.DataFrame({"date": df["date"].astype(int), "value": smb.round(4)})
out = out.sort_values("date").reset_index(drop=True)
out.to_csv("output.csv", index=False)
