import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_2x3.csv"

with open(fname, "r") as f:
    lines = f.read().splitlines()

# Locate the first block: "Average Value Weighted Returns -- Monthly"
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    # Fallback: first header line starting with a comma followed by data
    for i, line in enumerate(lines):
        if line.startswith(",") and re.match(r"^\d{6},", lines[i + 1].strip() if i + 1 < len(lines) else ""):
            start = i - 1
            break

# Find header line (starts with ',') after start
hdr = start + 1
while hdr < len(lines) and not lines[hdr].strip().startswith(","):
    hdr += 1
header = [c.strip() for c in lines[hdr].split(",")]

rows = []
j = hdr + 1
while j < len(lines):
    line = lines[j].strip()
    if line == "":
        break
    parts = [p.strip() for p in line.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        break
    vals = []
    for p in parts[1:]:
        try:
            vals.append(float(p))
        except ValueError:
            vals.append(np.nan)
    rows.append([int(parts[0])] + vals)
    j += 1

cols = ["date"] + header[1:len(rows[0])]
df = pd.DataFrame(rows, columns=cols)
df = df.replace([-99.99, -999.0], np.nan)

# Identify columns by name (robust to naming); fall back to positional order
def find_col(keys):
    for c in df.columns[1:]:
        cl = c.lower().replace(" ", "")
        if all(k in cl for k in keys):
            return c
    return None

SL = find_col(["small", "lobm"]) or df.columns[1]
SM = find_col(["me1", "bm2"]) or df.columns[2]
SH = find_col(["small", "hibm"]) or df.columns[3]
BL = find_col(["big", "lobm"]) or df.columns[4]
BM = find_col(["me2", "bm2"]) or df.columns[5]
BH = find_col(["big", "hibm"]) or df.columns[6]

smb = (df[SL] + df[SM] + df[SH]) / 3.0 - (df[BL] + df[BM] + df[BH]) / 3.0

out = pd.DataFrame({"date": df["date"].astype(int), "value": smb.round(4)})
out = out.dropna(subset=["value"])
out.to_csv("output.csv", index=False)
