import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [ln.rstrip("\r\n") for ln in f]

# Locate the first table: Average Value Weighted Returns -- Monthly
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# Header line follows (first line starting with a comma)
hdr_idx = None
for j in range(start + 1, min(start + 10, len(lines))):
    if lines[j].strip().startswith(","):
        hdr_idx = j
        break
if hdr_idx is None:
    raise RuntimeError("Header not found")

cols = [c.strip() for c in lines[hdr_idx].split(",")[1:]]

rows = []
for ln in lines[hdr_idx + 1:]:
    s = ln.strip()
    if not s:
        break
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    vals = []
    for p in parts[1:1 + len(cols)]:
        try:
            vals.append(float(p))
        except ValueError:
            vals.append(np.nan)
    rows.append([int(parts[0])] + vals)

df = pd.DataFrame(rows, columns=["date"] + cols)
for c in cols:
    df.loc[df[c].isin([-99.99, -999.0]), c] = np.nan

small = ["SMALL LoBM", "ME1 BM2", "SMALL HiBM"]
big = ["BIG LoBM", "ME2 BM2", "BIG HiBM"]

df["value"] = df[small].mean(axis=1, skipna=False) - df[big].mean(axis=1, skipna=False)
out = df[["date", "value"]].dropna().copy()
out["date"] = out["date"].astype(int)
out = out.drop_duplicates("date").sort_values("date")
out.to_csv("output.csv", index=False)
