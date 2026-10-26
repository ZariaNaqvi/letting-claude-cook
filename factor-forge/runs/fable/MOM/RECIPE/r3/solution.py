import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_Prior_12_2.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

# Locate the first monthly block: "Average Value Weighted Returns -- Monthly"
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    # fallback: first line that starts with a comma (header row)
    for i, line in enumerate(lines):
        if line.startswith(","):
            start = i - 1
            break

# header row is the next line that starts with a comma
hdr_idx = start + 1
while hdr_idx < len(lines) and not lines[hdr_idx].strip().startswith(","):
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].strip().split(",")]

rows = []
for line in lines[hdr_idx + 1:]:
    s = line.strip()
    if not s:
        # blank line ends the block (only stop if we already collected rows)
        if rows:
            break
        continue
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        # non-monthly row (e.g. annual block or new header) -> end of block
        if rows:
            break
        continue
    rows.append(parts)

df = pd.DataFrame(rows, columns=header)
df.rename(columns={header[0]: "date"}, inplace=True)
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Treat missing codes
for c in df.columns[1:]:
    df.loc[df[c].isin([-99.99, -999.0, -999]), c] = np.nan

def find_col(cols, must):
    for c in cols:
        cl = c.upper().replace(" ", "")
        if all(m in cl for m in must):
            return c
    raise KeyError(must)

cols = list(df.columns[1:])
small_hi = find_col(cols, ["SMALL", "HIPRIOR"])
big_hi = find_col(cols, ["BIG", "HIPRIOR"])
small_lo = find_col(cols, ["SMALL", "LOPRIOR"])
big_lo = find_col(cols, ["BIG", "LOPRIOR"])

df["value"] = 0.5 * (df[small_hi] + df[big_hi]) - 0.5 * (df[small_lo] + df[big_lo])

out = df[["date", "value"]].dropna(subset=["value"]).copy()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
