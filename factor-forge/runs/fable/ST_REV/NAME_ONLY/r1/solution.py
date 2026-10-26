import pandas as pd
import numpy as np

fname = "6_Portfolios_ME_Prior_1_0.csv"

with open(fname, "r") as f:
    lines = f.readlines()

# Locate the first (monthly value-weighted) block: header line starting with a comma,
# followed by rows whose first field is a 6-digit YYYYMM date.
start = None
for i, line in enumerate(lines):
    if line.strip().startswith(",") and "LoPRIOR" in line:
        start = i + 1
        break
if start is None:
    raise RuntimeError("Could not find monthly block header")

rows = []
for line in lines[start:]:
    s = line.strip()
    if not s:
        break
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 7 or not (parts[0].isdigit() and len(parts[0]) == 6):
        break
    try:
        vals = [float(p) for p in parts[1:]]
    except ValueError:
        break
    rows.append([int(parts[0])] + vals)

cols = ["date", "S_Lo", "S_Mid", "S_Hi", "B_Lo", "B_Mid", "B_Hi"]
df = pd.DataFrame(rows, columns=cols)

# Treat missing-data markers as NaN
for c in cols[1:]:
    df.loc[df[c].isin([-99.99, -999.0]), c] = np.nan

# ST_Rev = 1/2 (Small Low + Big Low) - 1/2 (Small High + Big High)
df["value"] = 0.5 * (df["S_Lo"] + df["B_Lo"]) - 0.5 * (df["S_Hi"] + df["B_Hi"])
df["value"] = df["value"].round(2)

out = df[["date", "value"]].dropna()
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
