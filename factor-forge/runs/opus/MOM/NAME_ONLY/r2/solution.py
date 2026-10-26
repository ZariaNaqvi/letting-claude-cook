import csv
import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_ME_Prior_12_2.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = f.read().splitlines()

# Locate first monthly value-weighted block
start = None
for i, ln in enumerate(lines):
    if "Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    # fallback: first header line beginning with ','
    for i, ln in enumerate(lines):
        if ln.strip().startswith(","):
            start = i - 1
            break

# header line is next line starting with ','
hdr_idx = start + 1
while not lines[hdr_idx].strip().startswith(","):
    hdr_idx += 1

rows = []
for ln in lines[hdr_idx + 1:]:
    s = ln.strip()
    if not s:
        break
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    try:
        vals = [float(x) for x in parts[1:7]]
    except ValueError:
        continue
    if len(vals) < 6:
        continue
    rows.append([int(parts[0])] + vals)

df = pd.DataFrame(rows, columns=["date", "SL", "SM", "SH", "BL", "BM", "BH"])
for c in ["SL", "SM", "SH", "BL", "BM", "BH"]:
    df.loc[(df[c] <= -99.99) | (df[c] == -999), c] = np.nan

df["value"] = 0.5 * (df["SH"] + df["BH"]) - 0.5 * (df["SL"] + df["BL"])
out = df[["date", "value"]].dropna().copy()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(6)
out = out.drop_duplicates("date").sort_values("date")
out.to_csv("output.csv", index=False)
