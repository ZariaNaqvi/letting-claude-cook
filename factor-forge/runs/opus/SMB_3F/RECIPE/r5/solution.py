import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [ln.rstrip("\r\n") for ln in f]

# Locate the first value-weighted monthly block
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns -- Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# Header line follows
hdr_idx = start + 1
while lines[hdr_idx].strip() == "":
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]
cols = header[1:]

rows = []
for ln in lines[hdr_idx + 1:]:
    s = ln.strip()
    if s == "":
        break
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    vals = []
    for p in parts[1:]:
        try:
            v = float(p)
        except ValueError:
            v = np.nan
        if v <= -99.99 or v == -999:
            v = np.nan
        vals.append(v)
    rows.append([int(parts[0])] + vals)

df = pd.DataFrame(rows, columns=["date"] + cols)

def col(name):
    for c in df.columns:
        if c.replace(" ", "").upper() == name.replace(" ", "").upper():
            return df[c]
    raise KeyError(name)

small = (col("SMALL LoBM") + col("ME1 BM2") + col("SMALL HiBM")) / 3.0
big = (col("BIG LoBM") + col("ME2 BM2") + col("BIG HiBM")) / 3.0
smb = small - big

out = pd.DataFrame({"date": df["date"].astype(int), "value": smb})
out = out.dropna(subset=["value"])
out = out.drop_duplicates(subset="date").sort_values("date")
out.to_csv("output.csv", index=False)
