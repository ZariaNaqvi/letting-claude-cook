import pandas as pd
import numpy as np

rows = []
header = None
with open("6_Portfolios_2x3.csv", "r") as f:
    lines = f.read().splitlines()

start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break

header = [h.strip() for h in lines[start + 1].split(",")]
for l in lines[start + 2:]:
    parts = [p.strip() for p in l.split(",")]
    if not parts or not parts[0].isdigit() or len(parts[0]) != 6:
        break
    rows.append(parts)

df = pd.DataFrame(rows, columns=header)
df.columns = ["date"] + list(df.columns[1:])
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c].isin([-99.99, -999]), c] = np.nan

df["value"] = 0.5 * (df["SMALL HiBM"] + df["BIG HiBM"]) - 0.5 * (df["SMALL LoBM"] + df["BIG LoBM"])
out = df[["date", "value"]].dropna()
out.to_csv("output.csv", index=False)
