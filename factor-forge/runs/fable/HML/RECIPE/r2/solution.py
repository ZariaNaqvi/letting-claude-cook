import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_2x3.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the first table: "Average Value Weighted Returns -- Monthly"
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    raise RuntimeError("Could not find the value-weighted monthly table")

# Header line follows (begins with a comma)
hdr_idx = None
for j in range(start + 1, min(start + 10, len(lines))):
    if lines[j].strip().startswith(","):
        hdr_idx = j
        break
if hdr_idx is None:
    raise RuntimeError("Could not find header line")

header = [h.strip() for h in lines[hdr_idx].split(",")]
header[0] = "date"

rows = []
for line in lines[hdr_idx + 1:]:
    s = line.strip()
    if s == "":
        # blank line ends the block (allow leading blanks? stop at first blank after data)
        if rows:
            break
        else:
            continue
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        # non-monthly row (e.g. annual YYYY or a new block title) -> stop
        break
    if len(parts) != len(header):
        break
    rows.append(parts)

df = pd.DataFrame(rows, columns=header)
df["date"] = df["date"].astype(int)
for c in header[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Treat missing codes as NaN
for c in header[1:]:
    df.loc[df[c] <= -99.0, c] = np.nan

hml = 0.5 * (df["SMALL HiBM"] + df["BIG HiBM"]) - 0.5 * (df["SMALL LoBM"] + df["BIG LoBM"])

out = pd.DataFrame({"date": df["date"].astype(int), "value": hml.round(4)})
out = out.dropna(subset=["value"])
out.to_csv("output.csv", index=False)
