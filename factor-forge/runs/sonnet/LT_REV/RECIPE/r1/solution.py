import pandas as pd
import numpy as np

fn = "6_Portfolios_ME_Prior_60_13.csv"
with open(fn, "r", errors="ignore") as f:
    lines = f.read().splitlines()

start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break

header = [h.strip() for h in lines[start + 1].split(",")]
rows = []
for l in lines[start + 2:]:
    parts = [p.strip() for p in l.split(",")]
    if len(parts) < 7 or not (parts[0].isdigit() and len(parts[0]) == 6):
        break
    rows.append(parts)

cols = ["date"] + header[1:]
df = pd.DataFrame(rows, columns=cols[:len(rows[0])])
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c].isin([-99.99, -999]), c] = np.nan

val = 0.5 * (df["SMALL LoPRIOR"] + df["BIG LoPRIOR"]) - 0.5 * (df["SMALL HiPRIOR"] + df["BIG HiPRIOR"])
out = pd.DataFrame({"date": df["date"], "value": val}).dropna()
out.to_csv("output.csv", index=False)
