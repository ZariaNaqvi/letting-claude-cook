import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = [l.rstrip("\r\n") for l in f]

# locate the value-weighted monthly section
start = None
for i, l in enumerate(lines):
    s = l.strip().lower()
    if "average value weighted returns" in s and "monthly" in s:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly section not found")

# header line: next non-empty line
j = start + 1
while lines[j].strip() == "":
    j += 1
header = [h.strip() for h in lines[j].split(",")]
cols = header[1:]

rows = []
k = j + 1
date_re = re.compile(r"^\s*(\d{6})\s*,")
while k < len(lines):
    l = lines[k]
    m = date_re.match(l)
    if not m:
        break
    parts = [p.strip() for p in l.split(",")]
    rows.append([int(parts[0])] + [float(p) if p not in ("",) else np.nan for p in parts[1:1 + len(cols)]])
    k += 1

df = pd.DataFrame(rows, columns=["date"] + cols)

def find_col(pattern_list):
    for c in cols:
        cu = c.upper().replace(" ", "")
        if all(p in cu for p in pattern_list):
            return c
    raise RuntimeError(f"column {pattern_list} not found in {cols}")

sl = find_col(["SMALL", "LOBM"]) if any("SMALL" in c.upper() for c in cols) else find_col(["ME1", "BM1"])
sh = find_col(["SMALL", "HIBM"]) if any("SMALL" in c.upper() for c in cols) else find_col(["ME1", "BM3"])
bl = find_col(["BIG", "LOBM"]) if any("BIG" in c.upper() for c in cols) else find_col(["ME2", "BM1"])
bh = find_col(["BIG", "HIBM"]) if any("BIG" in c.upper() for c in cols) else find_col(["ME2", "BM3"])

sub = df[["date", sl, sh, bl, bh]].copy()
for c in [sl, sh, bl, bh]:
    sub.loc[sub[c] <= -99.99, c] = np.nan
sub = sub.dropna()

sub["value"] = 0.5 * (sub[sh] + sub[bh]) - 0.5 * (sub[sl] + sub[bl])
out = sub[["date", "value"]].copy()
out["date"] = out["date"].astype(int)
out = out.drop_duplicates("date").sort_values("date")
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
