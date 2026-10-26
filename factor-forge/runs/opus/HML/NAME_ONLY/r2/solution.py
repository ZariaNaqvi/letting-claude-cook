import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [l.rstrip("\r\n") for l in f]

# locate the value-weighted monthly section
start = None
for i, l in enumerate(lines):
    s = l.lower()
    if "value weighted returns" in s and "monthly" in s:
        start = i
        break
if start is None:
    raise RuntimeError("Value weighted monthly section not found")

# header line: next non-empty line
j = start + 1
while j < len(lines) and lines[j].strip() == "":
    j += 1
header = [h.strip() for h in lines[j].split(",")]
cols = header[1:]

rows = []
k = j + 1
pat = re.compile(r"^\s*(\d{6})\s*,")
while k < len(lines):
    m = pat.match(lines[k])
    if not m:
        break
    parts = [p.strip() for p in lines[k].split(",")]
    date = int(parts[0])
    vals = []
    for p in parts[1:1 + len(cols)]:
        try:
            vals.append(float(p))
        except ValueError:
            vals.append(np.nan)
    while len(vals) < len(cols):
        vals.append(np.nan)
    rows.append([date] + vals)
    k += 1

df = pd.DataFrame(rows, columns=["date"] + cols)
for c in cols:
    df.loc[df[c] <= -99.99, c] = np.nan


def find_col(size_keys, bm_key):
    for c in cols:
        cu = c.upper().replace(" ", "")
        if any(cu.startswith(s) for s in size_keys) and cu.endswith(bm_key):
            return c
    raise RuntimeError(f"column not found {size_keys} {bm_key}")


sl = find_col(["SMALL", "ME1"], "LOBM")
sh = find_col(["SMALL", "ME1"], "HIBM")
bl = find_col(["BIG", "ME2"], "LOBM")
bh = find_col(["BIG", "ME2"], "HIBM")

hml = 0.5 * (df[sh] + df[bh]) - 0.5 * (df[sl] + df[bl])
out = pd.DataFrame({"date": df["date"].astype(int), "value": hml})
out = out.dropna(subset=["value"])
out = out.drop_duplicates(subset="date").sort_values("date")
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
