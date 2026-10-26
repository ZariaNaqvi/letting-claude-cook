import re
import numpy as np
import pandas as pd

FN = "6_Portfolios_ME_Prior_12_2.csv"

with open(FN, "r", encoding="latin-1") as f:
    lines = [l.rstrip("\r\n") for l in f]

# locate the monthly value-weighted block
start = None
for i, l in enumerate(lines):
    s = l.strip().lower()
    if "value weighted" in s and "monthly" in s and "average" in s:
        start = i
        break
if start is None:
    # fallback: first header line beginning with a comma
    for i, l in enumerate(lines):
        if l.strip().startswith(","):
            start = i - 1
            break

# header line
h = start + 1
while not lines[h].strip().startswith(","):
    h += 1
header = [c.strip() for c in lines[h].split(",")][1:]

rows = []
j = h + 1
while j < len(lines):
    l = lines[j]
    if not re.match(r"^\s*\d{6}\s*,", l):
        break
    parts = [p.strip() for p in l.split(",")]
    rows.append([int(parts[0])] + [float(x) if x not in ("",) else np.nan for x in parts[1:1 + len(header)]])
    j += 1

df = pd.DataFrame(rows, columns=["date"] + header)
vals = df[header].astype(float)
vals = vals.mask((vals <= -99.99 + 1e-9) | (vals == -999))

def find(cols, size_keys, prior_keys, default):
    for idx, c in enumerate(cols):
        cu = c.upper().replace(" ", "")
        if any(k in cu for k in size_keys) and any(k in cu for k in prior_keys):
            return c
    return cols[default]

SL = find(header, ["SMALL", "ME1"], ["LOPRIOR", "PRIOR1"], 0)
SH = find(header, ["SMALL", "ME1"], ["HIPRIOR", "PRIOR3"], 2)
BL = find(header, ["BIG", "ME2"], ["LOPRIOR", "PRIOR1"], 3)
BH = find(header, ["BIG", "ME2"], ["HIPRIOR", "PRIOR3"], 5)

mom = 0.5 * (vals[SH] + vals[BH]) - 0.5 * (vals[SL] + vals[BL])
out = pd.DataFrame({"date": df["date"].astype(int), "value": mom.round(2)})
out = out.dropna().drop_duplicates("date").sort_values("date")
out.to_csv("output.csv", index=False)
