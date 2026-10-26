import re
import pandas as pd
import numpy as np

fname = "6_Portfolios_ME_Prior_1_0.csv"

with open(fname, "r") as f:
    lines = f.readlines()

# Locate the first (value-weighted, monthly) block
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    # Fall back: first line that starts with a 6-digit date
    for i, line in enumerate(lines):
        if re.match(r"^\s*\d{6}\s*,", line):
            start = i - 1
            break

rows = []
started = False
for line in lines[start + 1:]:
    s = line.strip()
    if re.match(r"^\d{6}\s*,", s):
        started = True
        parts = [p.strip() for p in s.split(",")]
        try:
            date = int(parts[0])
            vals = [float(p) for p in parts[1:7]]
        except ValueError:
            continue
        rows.append([date] + vals)
    elif started:
        # end of the monthly block (blank line or new section header)
        if s == "" or not re.match(r"^\d{6}", s):
            break

cols = ["date", "S_Lo", "S_Mid", "S_Hi", "B_Lo", "B_Mid", "B_Hi"]
df = pd.DataFrame(rows, columns=cols)

# Treat missing codes as NaN
for c in cols[1:]:
    df.loc[df[c] <= -99.0, c] = np.nan

# ST_Rev = 1/2 (Small Low + Big Low) - 1/2 (Small High + Big High)
df["value"] = 0.5 * (df["S_Lo"] + df["B_Lo"]) - 0.5 * (df["S_Hi"] + df["B_Hi"])

out = df[["date", "value"]].dropna().copy()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(2)
out = out.sort_values("date").drop_duplicates("date")
out.to_csv("output.csv", index=False)
