import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_ME_Prior_12_2.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [l.rstrip("\r\n") for l in f]

# locate the monthly value-weighted section
start = None
for i, l in enumerate(lines):
    s = l.strip().lower()
    if "value weighted returns" in s and "monthly" in s:
        start = i
        break
if start is None:
    # fallback: first header line beginning with a comma
    for i, l in enumerate(lines):
        if l.strip().startswith(","):
            start = i - 1
            break

hdr_idx = start + 1
while not lines[hdr_idx].strip():
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]

rows = []
for l in lines[hdr_idx + 1:]:
    parts = [p.strip() for p in l.split(",")]
    if not parts or not re.fullmatch(r"\d{6}", parts[0]):
        break
    rows.append(parts)

cols = ["date"] + header[1:]
ncol = len(cols)
rows = [r[:ncol] for r in rows]
df = pd.DataFrame(rows, columns=cols)
df["date"] = df["date"].astype(int)
for c in cols[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

def find(size_key, prior_key, fallback_pos):
    for c in cols[1:]:
        cu = c.upper().replace(" ", "")
        if size_key in cu and prior_key in cu:
            return c
    return cols[fallback_pos]

sl = find("SMALL", "LOPRIOR", 1)
sh = find("SMALL", "HIPRIOR", 3)
bl = find("BIG", "LOPRIOR", 4)
bh = find("BIG", "HIPRIOR", 6)

sub = df[["date", sl, sh, bl, bh]].copy()
vals = sub[[sl, sh, bl, bh]]
bad = (vals <= -99.99) | vals.isna()
sub = sub[~bad.any(axis=1)]

mom = 0.5 * (sub[sh] + sub[bh]) - 0.5 * (sub[sl] + sub[bl])
out = pd.DataFrame({"date": sub["date"].astype(int), "value": np.round(mom.values, 2)})
out = out.drop_duplicates("date").sort_values("date")
out.to_csv("output.csv", index=False)
