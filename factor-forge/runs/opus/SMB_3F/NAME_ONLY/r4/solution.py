import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [l.rstrip("\r\n") for l in f]

# Locate the monthly value-weighted section
start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly section not found")

# Header line follows
hdr_idx = start + 1
while lines[hdr_idx].strip() == "":
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]

rows = []
for l in lines[hdr_idx + 1:]:
    parts = [p.strip() for p in l.split(",")]
    if len(parts) < 7 or not re.fullmatch(r"\d{6}", parts[0]):
        break
    rows.append(parts[:7])

cols = ["date"] + header[1:7]
df = pd.DataFrame(rows, columns=cols)
df["date"] = df["date"].astype(int)
for c in cols[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[(df[c] <= -99.99 + 1e-9) & (df[c] >= -99.99 - 1e-9), c] = np.nan
    df.loc[df[c] <= -999 + 1e-9, c] = np.nan

# Columns: SMALL LoBM, ME1 BM2, SMALL HiBM, BIG LoBM, ME2 BM2, BIG HiBM
vals = df[cols[1:]].to_numpy(dtype=float)
small = vals[:, 0:3].mean(axis=1)
big = vals[:, 3:6].mean(axis=1)
smb = small - big

out = pd.DataFrame({"date": df["date"].astype(int), "value": smb})
out = out.dropna(subset=["value"])
out = out.drop_duplicates(subset="date").sort_values("date")
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
