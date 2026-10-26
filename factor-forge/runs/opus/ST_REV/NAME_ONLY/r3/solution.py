import pandas as pd
import numpy as np

fname = "6_Portfolios_ME_Prior_1_0.csv"
with open(fname, "r", encoding="latin-1") as f:
    lines = f.read().splitlines()

# Locate the first monthly value-weighted block
start = None
for i, ln in enumerate(lines):
    if "Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Monthly VW block not found")

# header line
hdr_idx = start + 1
while not lines[hdr_idx].strip():
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]
cols = header[1:]

rows = []
for ln in lines[hdr_idx + 1:]:
    s = ln.strip()
    if not s:
        if rows:
            break
        continue
    parts = [p.strip() for p in s.split(",")]
    d = parts[0]
    if not (d.isdigit() and len(d) == 6):
        break
    vals = []
    for p in parts[1:1 + len(cols)]:
        try:
            vals.append(float(p))
        except ValueError:
            vals.append(np.nan)
    rows.append([int(d)] + vals)

df = pd.DataFrame(rows, columns=["date"] + cols)
for c in cols:
    df.loc[df[c] <= -99.99, c] = np.nan

def find(keys):
    for c in cols:
        u = c.upper().replace(" ", "")
        if all(k in u for k in keys):
            return c
    raise KeyError(keys)

sl = find(["SMALL", "LOPRIOR"])
sh = find(["SMALL", "HIPRIOR"])
bl = find(["BIG", "LOPRIOR"])
bh = find(["BIG", "HIPRIOR"])

df["value"] = 0.5 * (df[sl] + df[bl]) - 0.5 * (df[sh] + df[bh])
out = df[["date", "value"]].dropna().copy()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(2)
out = out.sort_values("date").drop_duplicates("date")
out.to_csv("output.csv", index=False)
