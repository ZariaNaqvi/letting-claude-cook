import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_ME_Prior_60_13.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = [ln.rstrip("\r\n") for ln in f]

# locate first value-weighted monthly block
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns -- Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# header line: next non-empty line
h = start + 1
while lines[h].strip() == "":
    h += 1
header = [c.strip() for c in lines[h].split(",")]

rows = []
j = h + 1
while j < len(lines):
    ln = lines[j]
    parts = [p.strip() for p in ln.split(",")]
    if not parts or not re.fullmatch(r"\d{6}", parts[0]):
        break
    rows.append(parts)
    j += 1

df = pd.DataFrame(rows, columns=header[: len(rows[0])] if len(header) >= len(rows[0]) else None)
df.columns = ["date"] + header[1:len(rows[0])]
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c].isin([-99.99, -999.0]) | (df[c] <= -99.99), c] = np.nan

def col(name):
    for c in df.columns:
        if c.upper().replace(" ", "") == name.upper().replace(" ", ""):
            return df[c]
    raise KeyError(name)

sl = col("SMALL LoPRIOR")
bl = col("BIG LoPRIOR")
sh = col("SMALL HiPRIOR")
bh = col("BIG HiPRIOR")

val = 0.5 * (sl + bl) - 0.5 * (sh + bh)
out = pd.DataFrame({"date": df["date"].astype(int), "value": val})
out = out.dropna(subset=["value"])
out = out.drop_duplicates(subset="date").sort_values("date")
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
