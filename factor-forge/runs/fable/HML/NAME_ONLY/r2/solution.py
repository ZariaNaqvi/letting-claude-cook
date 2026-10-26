import re
import pandas as pd

fname = "6_Portfolios_2x3.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

# Locate the first monthly value-weighted section
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    # fallback: first line that looks like a column header
    for i, line in enumerate(lines):
        if line.startswith(",") and "LoBM" in line:
            start = i - 1
            break

# Find the column header line after the section title
hdr = None
for j in range(start + 1, min(start + 10, len(lines))):
    if lines[j].strip().startswith(","):
        hdr = j
        break
cols = [c.strip() for c in lines[hdr].strip().split(",")]
cols[0] = "date"

rows = []
pat = re.compile(r"^\s*\d{6}\s*,")
for line in lines[hdr + 1:]:
    if pat.match(line):
        parts = [p.strip() for p in line.strip().split(",")]
        rows.append(parts)
    else:
        if line.strip() == "" and not rows:
            continue
        break

df = pd.DataFrame(rows, columns=cols)
df["date"] = df["date"].astype(int)
for c in cols[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Treat missing codes as NaN
for c in cols[1:]:
    df.loc[df[c] <= -99.0, c] = float("nan")

# Identify columns by name
def find_col(keys):
    for c in cols[1:]:
        cu = c.upper().replace(" ", "")
        if all(k in cu for k in keys):
            return c
    raise KeyError(keys)

sl = find_col(["SMALL", "LOBM"])
sh = find_col(["SMALL", "HIBM"])
bl = find_col(["BIG", "LOBM"])
bh = find_col(["BIG", "HIBM"])

hml = 0.5 * (df[sh] + df[bh]) - 0.5 * (df[sl] + df[bl])

out = pd.DataFrame({"date": df["date"], "value": hml})
out = out.dropna(subset=["value"])
out["date"] = out["date"].astype(int)
out = out.sort_values("date").reset_index(drop=True)
out.to_csv("output.csv", index=False)
