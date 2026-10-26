import re
import numpy as np
import pandas as pd

FILE = "6_Portfolios_ME_Prior_60_13.csv"
OUT = "output.csv"

with open(FILE, encoding="latin-1") as f:
    lines = f.read().splitlines()

# locate the FIRST value-weighted monthly block
start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns -- Monthly" in l:
        start = i
        break
if start is None:
    raise SystemExit("Value-weighted monthly block not found")

# header line: first non-empty line after the title
hdr_idx = None
for j in range(start + 1, len(lines)):
    if lines[j].strip():
        hdr_idx = j
        break
header = [h.strip() for h in lines[hdr_idx].split(",")]

def col(name):
    for k, h in enumerate(header):
        if h == name:
            return k
    raise KeyError(name)

c_SL = col("SMALL LoPRIOR")
c_SH = col("SMALL HiPRIOR")
c_BL = col("BIG LoPRIOR")
c_BH = col("BIG HiPRIOR")

records = []
started = False
for l in lines[hdr_idx + 1:]:
    parts = [p.strip() for p in l.split(",")]
    if parts and re.fullmatch(r"\d{6}", parts[0]):
        started = True
        records.append(parts)
    elif started:
        break  # end of the monthly block

def to_num(s):
    try:
        v = float(s)
    except ValueError:
        return np.nan
    if v <= -99.99 + 1e-9 and v >= -99.99 - 1e-9:
        return np.nan
    if v == -999:
        return np.nan
    return v

out_rows = []
for p in records:
    d = int(p[0])
    try:
        sl = to_num(p[c_SL]); sh = to_num(p[c_SH])
        bl = to_num(p[c_BL]); bh = to_num(p[c_BH])
    except IndexError:
        continue
    val = 0.5 * (sl + bl) - 0.5 * (sh + bh)
    if np.isnan(val):
        continue
    out_rows.append((d, val))

out = pd.DataFrame(out_rows, columns=["date", "value"])
out["date"] = out["date"].astype(int)
out.to_csv(OUT, index=False)
print(f"Wrote {len(out)} rows to {OUT}")
