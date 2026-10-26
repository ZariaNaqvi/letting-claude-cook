import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = [l.rstrip("\r\n") for l in f]

# locate the monthly value-weighted section
start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break
if start is None:
    raise RuntimeError("Monthly value-weighted section not found")

# header line
hdr_idx = start + 1
while hdr_idx < len(lines) and not lines[hdr_idx].strip():
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]

rows = []
for l in lines[hdr_idx + 1:]:
    parts = [p.strip() for p in l.split(",")]
    if not parts or not re.fullmatch(r"\d{6}", parts[0]):
        break
    rows.append(parts)

cols = ["date"] + header[1:]
df = pd.DataFrame(rows, columns=cols[:len(rows[0])])
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c] <= -99.99 + 1e-9, c] = np.nan  # missing codes -99.99 / -999

# columns: SMALL LoBM, ME1 BM2, SMALL HiBM, BIG LoBM, ME2 BM2, BIG HiBM
vals = df.iloc[:, 1:7].to_numpy(dtype=float)
small = vals[:, 0:3].mean(axis=1)
big = vals[:, 3:6].mean(axis=1)
smb = small - big

out = pd.DataFrame({"date": df["date"].astype(int), "value": smb})
out = out.dropna(subset=["value"])
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
