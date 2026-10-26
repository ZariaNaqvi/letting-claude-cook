import numpy as np
import pandas as pd

rows = []
with open("6_Portfolios_2x3.csv", "r", encoding="latin-1") as f:
    lines = f.read().splitlines()

start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break

header = [h.strip() for h in lines[start + 1].split(",")]
for l in lines[start + 2:]:
    parts = [p.strip() for p in l.split(",")]
    if not parts or not (len(parts[0]) == 6 and parts[0].isdigit()):
        break
    rows.append(parts[:len(header)])

df = pd.DataFrame(rows, columns=["date"] + header[1:])
df["date"] = df["date"].astype(int)
cols = header[1:]
for c in cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[(df[c] <= -99.99), c] = np.nan

hml = 0.5 * (df["SMALL HiBM"] + df["BIG HiBM"]) - 0.5 * (df["SMALL LoBM"] + df["BIG LoBM"])
out = pd.DataFrame({"date": df["date"], "value": hml}).dropna()
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
