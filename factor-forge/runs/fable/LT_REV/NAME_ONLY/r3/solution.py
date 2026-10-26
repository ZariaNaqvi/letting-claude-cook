import re
import pandas as pd
import numpy as np

fname = "6_Portfolios_ME_Prior_60_13.csv"

with open(fname, "r") as f:
    lines = f.read().splitlines()

# Locate the monthly value-weighted returns block (first block in the file)
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    # fallback: first header line starting with a comma
    for i, line in enumerate(lines):
        if line.startswith(","):
            start = i - 1
            break

rows = []
started = False
for line in lines[start + 1:]:
    s = line.strip()
    if not s:
        if started:
            break
        continue
    if s.startswith(","):
        # header row
        continue
    if re.match(r"^\d{6},", s):
        parts = [p.strip() for p in s.split(",")]
        if len(parts) < 7:
            continue
        try:
            vals = [float(p) for p in parts[1:7]]
        except ValueError:
            continue
        rows.append([int(parts[0])] + vals)
        started = True
    else:
        if started:
            break

df = pd.DataFrame(rows, columns=["date", "SL", "SM", "SH", "BL", "BM", "BH"])

# Handle missing markers
for c in ["SL", "SM", "SH", "BL", "BM", "BH"]:
    df.loc[df[c].isin([-99.99, -999.0, -999]), c] = np.nan

# LT_Rev = 1/2 (Small Low + Big Low) - 1/2 (Small High + Big High)
df["value"] = 0.5 * (df["SL"] + df["BL"]) - 0.5 * (df["SH"] + df["BH"])

out = df[["date", "value"]].dropna().copy()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
