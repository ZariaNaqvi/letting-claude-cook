import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = f.read().splitlines()

# Locate the first value-weighted monthly block
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns -- Monthly" in line:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

header = [h.strip() for h in lines[start + 1].split(",")]
cols = header[1:]

rows = []
date_re = re.compile(r"^\s*(\d{6})\s*,")
for line in lines[start + 2:]:
    m = date_re.match(line)
    if not m:
        break  # end of block (blank line or next table header)
    parts = [p.strip() for p in line.split(",")]
    date = int(parts[0])
    vals = []
    for p in parts[1:1 + len(cols)]:
        try:
            v = float(p)
        except ValueError:
            v = np.nan
        if v <= -99.99 or v == -999:
            v = np.nan
        vals.append(v)
    rows.append([date] + vals)

df = pd.DataFrame(rows, columns=["date"] + cols)

small = ["SMALL LoBM", "ME1 BM2", "SMALL HiBM"]
big = ["BIG LoBM", "ME2 BM2", "BIG HiBM"]

smb = df[small].mean(axis=1, skipna=False) - df[big].mean(axis=1, skipna=False)

out = pd.DataFrame({"date": df["date"].astype(int), "value": smb})
out = out.dropna(subset=["value"])
out = out.drop_duplicates(subset="date").sort_values("date")
out.to_csv("output.csv", index=False)
