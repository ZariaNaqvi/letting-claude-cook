import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_Prior_1_0.csv"

with open(fname, "r") as f:
    lines = f.readlines()

# Find the first monthly block: header line starting with ',' followed by YYYYMM rows
start = None
for i, line in enumerate(lines):
    if line.startswith(","):
        # check next line is a monthly row (6-digit date)
        if i + 1 < len(lines) and re.match(r"^\s*\d{6}\s*,", lines[i + 1]):
            start = i
            break

header = [h.strip() for h in lines[start].strip().split(",")]
rows = []
for line in lines[start + 1:]:
    s = line.strip()
    if not s:
        break
    if not re.match(r"^\d{6}\s*,", s):
        break
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != len(header):
        break
    rows.append(parts)

df = pd.DataFrame(rows, columns=header)
df = df.rename(columns={header[0]: "date"})
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Treat missing codes as NaN
for c in df.columns[1:]:
    df.loc[df[c].isin([-99.99, -999.0, -999]), c] = np.nan

sl = df["SMALL LoPRIOR"]
bl = df["BIG LoPRIOR"]
sh = df["SMALL HiPRIOR"]
bh = df["BIG HiPRIOR"]

value = 0.5 * (sl + bl) - 0.5 * (sh + bh)

out = pd.DataFrame({"date": df["date"].astype(int), "value": value.round(6)})
out = out.dropna(subset=["value"])
out.to_csv("output.csv", index=False)
