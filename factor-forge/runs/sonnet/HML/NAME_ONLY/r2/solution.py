import pandas as pd
import numpy as np

rows = []
with open("6_Portfolios_2x3.csv", "r") as f:
    lines = f.read().splitlines()

start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i + 1
        break

for l in lines[start:]:
    s = l.strip()
    if not s:
        if rows:
            break
        continue
    parts = [p.strip() for p in s.split(",")]
    if len(parts) >= 7 and parts[0].isdigit() and len(parts[0]) == 6:
        rows.append([int(parts[0])] + [float(x) for x in parts[1:7]])
    else:
        if rows:
            break

df = pd.DataFrame(rows, columns=["date", "SL", "SM", "SH", "BL", "BM", "BH"])
cols = ["SL", "SM", "SH", "BL", "BM", "BH"]
df[cols] = df[cols].where((df[cols] > -99) )
df["value"] = (df["SH"] + df["BH"]) / 2 - (df["SL"] + df["BL"]) / 2
out = df.dropna(subset=["value"])[["date", "value"]]
out.to_csv("output.csv", index=False)
