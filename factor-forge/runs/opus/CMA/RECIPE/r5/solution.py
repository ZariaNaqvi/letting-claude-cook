import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_ME_INV_2x3.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [ln.rstrip("\r\n") for ln in f]

# Locate the first table: value-weighted monthly returns
start = None
for i, ln in enumerate(lines):
    s = ln.strip().lower()
    if "value weighted returns" in s and "monthly" in s:
        start = i
        break
if start is None:
    raise RuntimeError("Could not find value-weighted monthly block")

# Header line
h = start + 1
while lines[h].strip() == "":
    h += 1
header = [c.strip() for c in lines[h].split(",")]
cols = header[1:]

rows = []
j = h + 1
date_re = re.compile(r"^\d{6}$")
while j < len(lines):
    ln = lines[j].strip()
    if ln == "":
        break
    parts = [p.strip() for p in ln.split(",")]
    if not date_re.match(parts[0]):
        break
    rows.append(parts)
    j += 1

df = pd.DataFrame([r[1:1 + len(cols)] for r in rows], columns=cols)
df = df.apply(pd.to_numeric, errors="coerce")
df.insert(0, "date", [int(r[0]) for r in rows])

def norm(c):
    return re.sub(r"\s+", " ", c.strip().upper())

colmap = {norm(c): c for c in cols}
sl = colmap["SMALL LOINV"]
sh = colmap["SMALL HIINV"]
bl = colmap["BIG LOINV"]
bh = colmap["BIG HIINV"]

sub = df[[sl, sh, bl, bh]].astype(float)
sub = sub.mask((sub <= -99.99 + 1e-9) | (sub == -999))

val = 0.5 * (sub[sl] + sub[bl]) - 0.5 * (sub[sh] + sub[bh])

out = pd.DataFrame({"date": df["date"].astype(int), "value": val})
out = out.dropna(subset=["value"])
out = out.drop_duplicates(subset="date").sort_values("date")
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
