import re
import pandas as pd
import numpy as np

fname = "6_Portfolios_2x3.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the "Average Value Weighted Returns -- Monthly" section
start = None
for i, line in enumerate(lines):
    s = line.strip().lower()
    if "average value weighted returns" in s and "monthly" in s:
        start = i
        break
if start is None:
    # fallback: first section after the description block
    for i, line in enumerate(lines):
        if re.match(r"^\s*\d{6}\s*,", line):
            start = i - 2
            break

# Parse the header line (column names) and data rows
header = None
rows = []
in_data = False
for line in lines[start + 1:]:
    stripped = line.strip()
    if not in_data:
        if stripped.startswith(","):
            header = [c.strip() for c in stripped.split(",")]
            continue
        if re.match(r"^\d{6}\s*,", stripped):
            in_data = True
        else:
            continue
    if in_data:
        m = re.match(r"^(\d{6})\s*,(.*)$", stripped)
        if not m:
            # end of monthly section
            break
        date = int(m.group(1))
        vals = [v.strip() for v in m.group(2).split(",")]
        try:
            vals = [float(v) for v in vals]
        except ValueError:
            break
        rows.append([date] + vals)

cols = ["date", "SMALL LoBM", "ME1 BM2", "SMALL HiBM", "BIG LoBM", "ME2 BM2", "BIG HiBM"]
df = pd.DataFrame(rows, columns=cols[:len(rows[0])])

# Treat missing values
for c in df.columns[1:]:
    df.loc[df[c] <= -99.0, c] = np.nan

# HML = 1/2 (Small Value + Big Value) - 1/2 (Small Growth + Big Growth)
hml = 0.5 * (df["SMALL HiBM"] + df["BIG HiBM"]) - 0.5 * (df["SMALL LoBM"] + df["BIG LoBM"])

out = pd.DataFrame({"date": df["date"].astype(int), "value": hml.round(4)})
out = out.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)
out.to_csv("output.csv", index=False)
