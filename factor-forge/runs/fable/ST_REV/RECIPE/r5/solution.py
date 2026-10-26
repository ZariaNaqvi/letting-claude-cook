import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_Prior_1_0.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the first (value-weighted monthly) block: header line starting with a comma
# followed by rows beginning with 6-digit YYYYMM dates.
start = None
for i, line in enumerate(lines):
    if line.strip().startswith(",") and "LoPRIOR" in line:
        start = i
        break
if start is None:
    raise RuntimeError("Could not find header of first table")

header = [h.strip() for h in lines[start].split(",")]
rows = []
for line in lines[start + 1:]:
    s = line.strip()
    if not s:
        break
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    rows.append(parts)

df = pd.DataFrame(rows, columns=header)
df = df.rename(columns={header[0]: "date"})
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Treat missing indicators as NaN
for c in df.columns[1:]:
    df.loc[df[c] <= -99.0, c] = np.nan

def find_col(pattern):
    for c in df.columns[1:]:
        if re.fullmatch(pattern, c, flags=re.IGNORECASE):
            return c
    raise RuntimeError(f"Column matching {pattern} not found: {list(df.columns)}")

s_lo = find_col(r"SMALL\s+LoPRIOR")
s_hi = find_col(r"SMALL\s+HiPRIOR")
b_lo = find_col(r"BIG\s+LoPRIOR")
b_hi = find_col(r"BIG\s+HiPRIOR")

df["value"] = 0.5 * (df[s_lo] + df[b_lo]) - 0.5 * (df[s_hi] + df[b_hi])

out = df[["date", "value"]].dropna(subset=["value"]).copy()
out["date"] = out["date"].astype(int)
out = out.sort_values("date").reset_index(drop=True)
out.to_csv("output.csv", index=False)
