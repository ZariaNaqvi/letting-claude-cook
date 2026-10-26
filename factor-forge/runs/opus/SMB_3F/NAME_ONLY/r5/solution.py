import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the first monthly value-weighted block
start = None
for i, ln in enumerate(lines):
    s = ln.lower()
    if "value weighted returns" in s and "monthly" in s:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly section not found")

# Header line is the next non-empty line
j = start + 1
while j < len(lines) and lines[j].strip() == "":
    j += 1
header = [h.strip() for h in lines[j].split(",")]
cols = header[1:]
j += 1

rows = []
date_re = re.compile(r"^\s*(\d{6})\s*$")
while j < len(lines):
    parts = lines[j].split(",")
    if len(parts) < 2 or not date_re.match(parts[0]):
        break
    d = int(parts[0].strip())
    vals = []
    for p in parts[1:1 + len(cols)]:
        try:
            vals.append(float(p.strip()))
        except ValueError:
            vals.append(np.nan)
    rows.append([d] + vals)
    j += 1

df = pd.DataFrame(rows, columns=["date"] + cols)
for c in cols:
    df.loc[df[c] <= -99.99, c] = np.nan

def find(name_opts, default_idx):
    for c in cols:
        cn = c.upper().replace(" ", "")
        for n in name_opts:
            if cn == n.upper().replace(" ", ""):
                return c
    return cols[default_idx]

s_lo = find(["SMALL LoBM", "ME1 BM1"], 0)
s_mid = find(["ME1 BM2"], 1)
s_hi = find(["SMALL HiBM", "ME1 BM3"], 2)
b_lo = find(["BIG LoBM", "ME2 BM1"], 3)
b_mid = find(["ME2 BM2"], 4)
b_hi = find(["BIG HiBM", "ME2 BM3"], 5)

smb = (df[s_lo] + df[s_mid] + df[s_hi]) / 3.0 - (df[b_lo] + df[b_mid] + df[b_hi]) / 3.0

out = pd.DataFrame({"date": df["date"].astype(int), "value": smb})
out = out.dropna(subset=["value"])
out = out.drop_duplicates(subset="date").sort_values("date")
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
