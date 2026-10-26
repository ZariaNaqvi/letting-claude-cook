import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_ME_Prior_1_0.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the first (value-weighted monthly) block
start = None
for i, ln in enumerate(lines):
    if "Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    # fallback: first header line beginning with a comma
    for i, ln in enumerate(lines):
        if ln.strip().startswith(",") and "PRIOR" in ln.upper():
            start = i - 1
            break

# header line
hdr_idx = start + 1
while not lines[hdr_idx].strip().startswith(","):
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]

rows = []
for ln in lines[hdr_idx + 1:]:
    s = ln.strip()
    if not s:
        break
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    vals = []
    for p in parts[1:]:
        try:
            vals.append(float(p))
        except ValueError:
            vals.append(np.nan)
    rows.append([int(parts[0])] + vals)

cols = ["date"] + header[1:len(rows[0])]
df = pd.DataFrame(rows, columns=cols)

def find_col(size_key, prior_key):
    for c in df.columns[1:]:
        u = c.upper().replace(" ", "")
        if size_key in u and prior_key in u:
            return c
    return None

# Columns: SMALL LoPRIOR, ME1 PRIOR2, SMALL HiPRIOR, BIG LoPRIOR, ME2 PRIOR2, BIG HiPRIOR
data_cols = list(df.columns[1:])
sl = find_col("SMALL", "LOPRIOR") or data_cols[0]
sh = find_col("SMALL", "HIPRIOR") or data_cols[2]
bl = find_col("BIG", "LOPRIOR") or data_cols[3]
bh = find_col("BIG", "HIPRIOR") or data_cols[5]

for c in [sl, sh, bl, bh]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[(df[c] <= -99.99) | (df[c] == -999), c] = np.nan

df["value"] = 0.5 * (df[sl] + df[bl]) - 0.5 * (df[sh] + df[bh])
out = df[["date", "value"]].dropna().copy()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(4)
out = out.sort_values("date").drop_duplicates("date")
out.to_csv("output.csv", index=False)
