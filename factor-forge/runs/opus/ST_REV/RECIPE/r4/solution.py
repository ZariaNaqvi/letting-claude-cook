import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_ME_Prior_1_0.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [l.rstrip("\r\n") for l in f]

# locate the first block: "Average Value Weighted Returns -- Monthly"
start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# header line follows
hdr_idx = start + 1
while lines[hdr_idx].strip() == "":
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]
cols = header[1:]

rows = []
for l in lines[hdr_idx + 1:]:
    s = l.strip()
    if s == "":
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

df = pd.DataFrame(rows, columns=["date"] + cols)
for c in cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c].isin([-99.99, -999.0]) | (df[c] <= -99.99), c] = np.nan

def find(name):
    for c in cols:
        if c.replace(" ", "").upper() == name.replace(" ", "").upper():
            return c
    raise KeyError(name)

sl, sh = find("SMALL LoPRIOR"), find("SMALL HiPRIOR")
bl, bh = find("BIG LoPRIOR"), find("BIG HiPRIOR")

df["value"] = 0.5 * (df[sl] + df[bl]) - 0.5 * (df[sh] + df[bh])
out = df[["date", "value"]].dropna().copy()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(6)
out = out.sort_values("date").drop_duplicates("date")
out.to_csv("output.csv", index=False)
