import re
import pandas as pd
import numpy as np

fname = "6_Portfolios_ME_Prior_1_0.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the first monthly value-weighted section
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    # fallback: first header line beginning with a comma
    for i, ln in enumerate(lines):
        if ln.startswith(","):
            start = i - 1
            break

# Find header line (starts with comma) after the section title
hdr_idx = None
for j in range(start + 1, min(start + 10, len(lines))):
    if lines[j].strip().startswith(","):
        hdr_idx = j
        break
header = [h.strip() for h in lines[hdr_idx].split(",")]
ncol = len(header)

rows = []
pat = re.compile(r"^\s*(\d{6})\s*,")
for ln in lines[hdr_idx + 1:]:
    if not ln.strip():
        if rows:
            break
        continue
    m = pat.match(ln)
    if not m:
        break
    parts = [p.strip() for p in ln.split(",")]
    if len(parts) < ncol:
        break
    try:
        vals = [float(p) for p in parts[1:ncol]]
    except ValueError:
        break
    rows.append([int(parts[0])] + vals)

df = pd.DataFrame(rows, columns=["date"] + header[1:])
df = df.set_index("date")

# Replace missing codes with NaN
df = df.replace([-99.99, -999.0, -999], np.nan)

cols = list(df.columns)
# Identify the needed portfolios by position/name:
# order: SMALL LoPRIOR, ME1 PRIOR2, SMALL HiPRIOR, BIG LoPRIOR, ME2 PRIOR2, BIG HiPRIOR
def find(name_sub, fallback_idx):
    for c in cols:
        if c.replace(" ", "").upper() == name_sub.replace(" ", "").upper():
            return c
    return cols[fallback_idx]

s_lo = find("SMALL LoPRIOR", 0)
s_hi = find("SMALL HiPRIOR", 2)
b_lo = find("BIG LoPRIOR", 3)
b_hi = find("BIG HiPRIOR", 5)

st_rev = 0.5 * (df[s_lo] + df[b_lo]) - 0.5 * (df[s_hi] + df[b_hi])
out = st_rev.dropna().reset_index()
out.columns = ["date", "value"]
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(2)
out = out.sort_values("date")
out.to_csv("output.csv", index=False)
