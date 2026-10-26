import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_2x3.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

# Locate the first table: "Average Value Weighted Returns -- Monthly"
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    raise RuntimeError("Could not find monthly value-weighted table")

# Header line is the next line starting with a comma
hdr_idx = start + 1
while hdr_idx < len(lines) and not lines[hdr_idx].strip().startswith(","):
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].strip().split(",")]

rows = []
for line in lines[hdr_idx + 1:]:
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

# Map column names robustly
cols = {c.upper().replace(" ", ""): c for c in df.columns[1:]}
def find(key):
    for k, v in cols.items():
        if k == key.upper().replace(" ", ""):
            return v
    raise KeyError(key)

sl = find("SMALL LoBM")
sh = find("SMALL HiBM")
bl = find("BIG LoBM")
bh = find("BIG HiBM")

sub = df[["date", sl, sh, bl, bh]].copy()
# Treat missing markers as NaN
for c in [sl, sh, bl, bh]:
    sub.loc[sub[c] <= -99.0, c] = np.nan

sub["value"] = 0.5 * (sub[sh] + sub[bh]) - 0.5 * (sub[sl] + sub[bl])
out = sub[["date", "value"]].dropna()
out["date"] = out["date"].astype(int)
out = out.sort_values("date").reset_index(drop=True)
out.to_csv("output.csv", index=False)
