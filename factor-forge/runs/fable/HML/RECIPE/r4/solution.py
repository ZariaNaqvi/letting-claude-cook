import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_2x3.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the first monthly table: header line starting with ',' followed by rows of form YYYYMM,...
start = None
for i, line in enumerate(lines):
    if line.strip().startswith(","):
        # check next line is a monthly row
        if i + 1 < len(lines) and re.match(r"^\s*\d{6}\s*,", lines[i + 1]):
            start = i
            break
if start is None:
    raise RuntimeError("Could not find monthly table header")

header = [h.strip() for h in lines[start].split(",")]
rows = []
for line in lines[start + 1:]:
    s = line.strip()
    if not s:
        break
    m = re.match(r"^(\d{6})\s*,(.*)$", s)
    if not m:
        break
    date = int(m.group(1))
    vals = [float(v.strip()) if v.strip() != "" else np.nan for v in m.group(2).split(",")]
    rows.append([date] + vals)

df = pd.DataFrame(rows, columns=["date"] + header[1:])

# Treat missing markers
for c in df.columns[1:]:
    df.loc[df[c] <= -99.0, c] = np.nan

small_hi = df["SMALL HiBM"]
big_hi = df["BIG HiBM"]
small_lo = df["SMALL LoBM"]
big_lo = df["BIG LoBM"]

hml = 0.5 * (small_hi + big_hi) - 0.5 * (small_lo + big_lo)

out = pd.DataFrame({"date": df["date"].astype(int), "value": hml.round(6)})
out = out.dropna(subset=["value"])
out.to_csv("output.csv", index=False)
