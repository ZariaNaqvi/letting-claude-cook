import pandas as pd
import numpy as np

SRC = "6_Portfolios_2x3.csv"
OUT = "output.csv"
TITLE = "Average Value Weighted Returns -- Monthly"

with open(SRC, encoding="latin-1") as f:
    lines = f.read().splitlines()

# locate the first monthly value-weighted block
start = None
for i, line in enumerate(lines):
    if TITLE.lower() in line.lower():
        start = i
        break
if start is None:
    raise SystemExit("Value-weighted monthly block not found")

# header: first subsequent line that starts with a comma (column names line)
hdr_idx = None
for j in range(start + 1, len(lines)):
    if lines[j].strip().startswith(","):
        hdr_idx = j
        break
if hdr_idx is None:
    raise SystemExit("Header line not found")

header = [h.strip() for h in lines[hdr_idx].split(",")]
col_pos = {name: k for k, name in enumerate(header)}
needed = ["SMALL LoBM", "SMALL HiBM", "BIG LoBM", "BIG HiBM"]
for n in needed:
    if n not in col_pos:
        raise SystemExit(f"Missing column {n}")

records = []
for line in lines[hdr_idx + 1:]:
    parts = [p.strip() for p in line.split(",")]
    if not parts or not parts[0].isdigit() or len(parts[0]) != 6:
        # end of monthly block (blank line, annual section, or footer)
        if records:
            break
        else:
            continue
    date = int(parts[0])
    vals = {}
    for n in needed:
        k = col_pos[n]
        try:
            v = float(parts[k])
        except (IndexError, ValueError):
            v = np.nan
        if v <= -99 or np.isnan(v):
            v = np.nan
        vals[n] = v
    records.append((date, vals))

rows = []
for date, vals in records:
    sh = vals["SMALL HiBM"]
    bh = vals["BIG HiBM"]
    sl = vals["SMALL LoBM"]
    bl = vals["BIG LoBM"]
    if np.isnan([sh, bh, sl, bl]).any():
        continue
    hml = 0.5 * (sh + bh) - 0.5 * (sl + bl)
    rows.append((date, hml))

out = pd.DataFrame(rows, columns=["date", "value"])
out["date"] = out["date"].astype(int)
out.to_csv(OUT, index=False, columns=["date", "value"])
