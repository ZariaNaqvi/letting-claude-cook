import pandas as pd
import numpy as np

fname = "6_Portfolios_2x3.csv"
with open(fname, "r", encoding="latin-1") as f:
    lines = [l.rstrip("\r\n") for l in f]

# locate the value-weighted monthly section
start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly section not found")

# header line
hdr_idx = start + 1
while lines[hdr_idx].strip() == "":
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]

rows = []
for l in lines[hdr_idx + 1:]:
    s = l.strip()
    if s == "":
        break
    parts = [p.strip() for p in s.split(",")]
    if not (len(parts[0]) == 6 and parts[0].isdigit()):
        break
    rows.append(parts)

df = pd.DataFrame(rows, columns=header[:len(rows[0])])
df = df.rename(columns={df.columns[0]: "date"})
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

vals = df.columns[1:]
# missing-data codes
df[vals] = df[vals].where(~df[vals].isin([-99.99, -999.0]), np.nan)
df[vals] = df[vals].where(df[vals] > -99.0, np.nan)

# column order: SMALL LoBM, ME1 BM2, SMALL HiBM, BIG LoBM, ME2 BM2, BIG HiBM
small = df[vals[0:3]]
big = df[vals[3:6]]
smb = small.mean(axis=1, skipna=False) - big.mean(axis=1, skipna=False)

out = pd.DataFrame({"date": df["date"], "value": smb})
out = out.dropna()
out["value"] = out["value"].round(4)
out = out.sort_values("date").drop_duplicates("date")
out.to_csv("output.csv", index=False)
