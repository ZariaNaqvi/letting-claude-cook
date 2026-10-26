import pandas as pd
import numpy as np

rows = []
header = None
started = False
with open("6_Portfolios_2x3.csv", "r", errors="ignore") as f:
    lines = f.read().splitlines()

i = 0
while i < len(lines):
    if "Average Value Weighted Returns" in lines[i] and "Monthly" in lines[i]:
        header = [h.strip() for h in lines[i + 1].split(",")]
        i += 2
        break
    i += 1

while i < len(lines):
    line = lines[i].strip()
    i += 1
    if not line:
        if started:
            break
        continue
    parts = [p.strip() for p in line.split(",")]
    if len(parts[0]) == 6 and parts[0].isdigit():
        started = True
        rows.append(parts)
    elif started:
        break

df = pd.DataFrame(rows, columns=header[:len(rows[0])])
date_col = df.columns[0]
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c] <= -99.0, c] = np.nan

val = 0.5 * (df["SMALL HiBM"] + df["BIG HiBM"]) - 0.5 * (df["SMALL LoBM"] + df["BIG LoBM"])
out = pd.DataFrame({"date": df[date_col].astype(int), "value": val})
out = out.dropna().reset_index(drop=True)
out.to_csv("output.csv", index=False)
