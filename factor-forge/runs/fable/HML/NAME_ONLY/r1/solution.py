import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_2x3.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the monthly value-weighted section
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Monthly value-weighted section not found")

# Header line (column names) is the next non-empty line
j = start + 1
while j < len(lines) and lines[j].strip() == "":
    j += 1
header = [c.strip() for c in lines[j].split(",")]
j += 1

rows = []
pat = re.compile(r"^\s*(\d{6})\s*,")
while j < len(lines):
    ln = lines[j]
    if ln.strip() == "":
        break
    m = pat.match(ln)
    if not m:
        break
    parts = [p.strip() for p in ln.split(",")]
    date = int(parts[0])
    vals = []
    for p in parts[1:]:
        try:
            vals.append(float(p))
        except ValueError:
            vals.append(np.nan)
    rows.append([date] + vals)
    j += 1

ncols = len(header)
df = pd.DataFrame(rows, columns=header[:ncols] if len(rows[0]) == ncols else ["date"] + header[1:len(rows[0])])
df = df.rename(columns={df.columns[0]: "date"})

cols = list(df.columns[1:])
# Expected order: SMALL LoBM, ME1 BM2, SMALL HiBM, BIG LoBM, ME2 BM2, BIG HiBM
def find(colnames, *keys):
    for c in colnames:
        cu = c.upper().replace(" ", "")
        if all(k in cu for k in keys):
            return c
    return None

sl = find(cols, "SMALL", "LOBM") or cols[0]
sh = find(cols, "SMALL", "HIBM") or cols[2]
bl = find(cols, "BIG", "LOBM") or cols[3]
bh = find(cols, "BIG", "HIBM") or cols[5]

for c in cols:
    df.loc[df[c] <= -99.0, c] = np.nan

hml = 0.5 * (df[sh] + df[bh]) - 0.5 * (df[sl] + df[bl])

out = pd.DataFrame({"date": df["date"].astype(int), "value": hml.round(4)})
out = out.dropna(subset=["value"])
out.to_csv("output.csv", index=False)
