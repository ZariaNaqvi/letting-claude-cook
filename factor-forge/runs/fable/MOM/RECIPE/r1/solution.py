import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_Prior_12_2.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate first monthly table: header line starting with comma, followed by YYYYMM rows
start = None
header = None
for i, line in enumerate(lines):
    s = line.strip()
    if s.startswith(",") and "SMALL LoPRIOR" in s:
        # check next line is a monthly row
        if i + 1 < len(lines) and re.match(r"^\s*\d{6}\s*,", lines[i + 1]):
            start = i + 1
            header = [h.strip() for h in s.split(",")]
            break

if start is None:
    raise RuntimeError("Could not find monthly value-weighted table")

rows = []
for line in lines[start:]:
    s = line.strip()
    if not s:
        break
    if not re.match(r"^\d{6}\s*,", s):
        break
    parts = [p.strip() for p in s.split(",")]
    rows.append(parts)

df = pd.DataFrame(rows, columns=header)
df = df.rename(columns={header[0]: "date"})
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Replace missing indicators
for c in df.columns[1:]:
    df.loc[df[c].isin([-99.99, -999, -999.0]), c] = np.nan

sh = df["SMALL HiPRIOR"]
bh = df["BIG HiPRIOR"]
sl = df["SMALL LoPRIOR"]
bl = df["BIG LoPRIOR"]

df["value"] = 0.5 * (sh + bh) - 0.5 * (sl + bl)

out = df[["date", "value"]].dropna()
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
