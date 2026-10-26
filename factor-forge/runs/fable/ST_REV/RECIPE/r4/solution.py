import pandas as pd
import numpy as np

fname = "6_Portfolios_ME_Prior_1_0.csv"

with open(fname, "r") as f:
    lines = f.readlines()

# Find the first block: 'Average Value Weighted Returns -- Monthly'
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns -- Monthly" in line:
        start = i
        break
if start is None:
    raise RuntimeError("Could not find the monthly value-weighted block")

# Header line is the next line
header_idx = start + 1
header = [h.strip() for h in lines[header_idx].strip().split(",")]

rows = []
for line in lines[header_idx + 1:]:
    s = line.strip()
    if s == "":
        break
    parts = [p.strip() for p in s.split(",")]
    if not parts[0].isdigit() or len(parts[0]) != 6:
        break
    rows.append(parts)

df = pd.DataFrame(rows, columns=header)
df = df.rename(columns={header[0]: "date"})
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Handle missing values
for c in df.columns[1:]:
    df.loc[df[c].isin([-99.99, -999.0]), c] = np.nan

sl = df["SMALL LoPRIOR"]
bl = df["BIG LoPRIOR"]
sh = df["SMALL HiPRIOR"]
bh = df["BIG HiPRIOR"]

value = 0.5 * (sl + bl) - 0.5 * (sh + bh)

out = pd.DataFrame({"date": df["date"].astype(int), "value": value.round(4)})
out = out.dropna(subset=["value"])
out.to_csv("output.csv", index=False)
