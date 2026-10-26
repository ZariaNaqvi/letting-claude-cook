import pandas as pd
import numpy as np
import re

rows = []
with open("6_Portfolios_2x3.csv", "r", errors="ignore") as f:
    lines = f.read().splitlines()

start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break

i = start + 2  # skip title and header
while i < len(lines):
    parts = [p.strip() for p in lines[i].split(",")]
    if len(parts) >= 7 and re.fullmatch(r"\d{6}", parts[0]):
        rows.append(parts[:7])
        i += 1
    else:
        break

df = pd.DataFrame(rows, columns=["date", "SL", "S2", "SH", "BL", "B2", "BH"])
df["date"] = df["date"].astype(int)
for c in ["SL", "S2", "SH", "BL", "B2", "BH"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c] <= -99.0, c] = np.nan

df["value"] = 0.5 * (df["SH"] + df["BH"]) - 0.5 * (df["SL"] + df["BL"])
out = df[["date", "value"]].dropna()
out.to_csv("output.csv", index=False)
