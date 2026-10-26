import pandas as pd
import numpy as np

FNAME = "6_Portfolios_ME_Prior_1_0.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [l.rstrip("\r\n") for l in f]

# Locate the monthly value-weighted section
start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break
if start is None:
    raise RuntimeError("Monthly VW section not found")

header = [h.strip() for h in lines[start + 1].split(",")]
rows = []
for l in lines[start + 2:]:
    s = l.strip()
    if not s:
        break
    parts = [p.strip() for p in s.split(",")]
    if not (parts[0].isdigit() and len(parts[0]) == 6):
        break
    rows.append(parts)

cols = ["date"] + header[1:]
df = pd.DataFrame(rows, columns=cols[:len(rows[0])])
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[(df[c] <= -99.99) | (df[c] == -999), c] = np.nan

def find(cands):
    for c in df.columns:
        cu = c.upper().replace(" ", "")
        for cand in cands:
            if cu == cand:
                return c
    raise KeyError(cands)

sl = find(["SMALLLOPRIOR", "ME1PRIOR1"])
sh = find(["SMALLHIPRIOR", "ME1PRIOR3"])
bl = find(["BIGLOPRIOR", "ME2PRIOR1"])
bh = find(["BIGHIPRIOR", "ME2PRIOR3"])

df["value"] = 0.5 * (df[sl] + df[bl]) - 0.5 * (df[sh] + df[bh])
out = df[["date", "value"]].dropna().copy()
out["value"] = out["value"].round(6)
out = out.sort_values("date").drop_duplicates("date")
out.to_csv("output.csv", index=False)
