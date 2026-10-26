import pandas as pd
import numpy as np

FNAME = "6_Portfolios_ME_Prior_60_13.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [l.rstrip("\r\n") for l in f]

# locate the monthly value-weighted section
start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break
if start is None:
    # fallback: first header line starting with ','
    for i, l in enumerate(lines):
        if l.strip().startswith(","):
            start = i - 1
            break

# header line
hdr_idx = start + 1
while not lines[hdr_idx].strip().startswith(","):
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")[1:]]

rows = []
for l in lines[hdr_idx + 1:]:
    parts = [p.strip() for p in l.split(",")]
    if len(parts) < 2 or not (parts[0].isdigit() and len(parts[0]) == 6):
        break
    try:
        vals = [float(p) for p in parts[1:1 + len(header)]]
    except ValueError:
        break
    rows.append([int(parts[0])] + vals)

df = pd.DataFrame(rows, columns=["date"] + header)

def find_col(keys):
    for c in header:
        cu = c.upper().replace(" ", "")
        if all(k in cu for k in keys):
            return c
    raise KeyError(keys)

sl = find_col(["SMALL", "LOPRIOR"])
sh = find_col(["SMALL", "HIPRIOR"])
bl = find_col(["BIG", "LOPRIOR"])
bh = find_col(["BIG", "HIPRIOR"])

sub = df[["date", sl, sh, bl, bh]].copy()
for c in [sl, sh, bl, bh]:
    sub.loc[(sub[c] <= -99.99 + 1e-9) | (sub[c] == -999), c] = np.nan
sub = sub.dropna()

sub["value"] = 0.5 * (sub[sl] + sub[bl]) - 0.5 * (sub[sh] + sub[bh])
out = sub[["date", "value"]].copy()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(4)
out = out.sort_values("date").drop_duplicates("date")
out.to_csv("output.csv", index=False)
