import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_2x3.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Find the first table: "Average Value Weighted Returns -- Monthly"
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    raise RuntimeError("Could not find monthly value-weighted table")

# Header line follows the title
header_idx = start + 1
while header_idx < len(lines) and not lines[header_idx].strip().startswith(","):
    header_idx += 1
header = [h.strip() for h in lines[header_idx].split(",")]

rows = []
for line in lines[header_idx + 1:]:
    s = line.strip()
    if not s:
        # blank line ends the block (next block follows)
        break
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    rows.append(parts)

df = pd.DataFrame(rows, columns=header[:len(rows[0])])
df = df.rename(columns={header[0]: "date"})
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Treat missing codes as NaN
vals = df.columns[1:]
df[vals] = df[vals].where(~df[vals].isin([-99.99, -999.0]), np.nan)

sh = df["SMALL HiBM"]
bh = df["BIG HiBM"]
sl = df["SMALL LoBM"]
bl = df["BIG LoBM"]

hml = 0.5 * (sh + bh) - 0.5 * (sl + bl)

out = pd.DataFrame({"date": df["date"].astype(int), "value": hml})
out = out.dropna(subset=["value"])
out.to_csv("output.csv", index=False)
