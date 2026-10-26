import csv
import numpy as np
import pandas as pd

rows = []
header = None
started = False
with open("6_Portfolios_ME_Prior_12_2.csv", newline="") as f:
    for line in f:
        s = line.strip()
        if not started:
            if s.startswith(",") and "SMALL" in s.upper() and "LoPRIOR".upper() in s.upper():
                header = [x.strip() for x in s.split(",")]
                started = True
            continue
        if not s:
            if rows:
                break
            continue
        parts = [x.strip() for x in s.split(",")]
        if not parts[0].isdigit() or len(parts[0]) != 6:
            if rows:
                break
            continue
        rows.append(parts)

df = pd.DataFrame(rows, columns=header)
df = df.rename(columns={header[0]: "date"})
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    v = pd.to_numeric(df[c], errors="coerce")
    v = v.where(~v.isin([-99.99, -999, -999.0]), np.nan)
    df[c] = v

val = 0.5 * (df["SMALL HiPRIOR"] + df["BIG HiPRIOR"]) - 0.5 * (df["SMALL LoPRIOR"] + df["BIG LoPRIOR"])
out = pd.DataFrame({"date": df["date"], "value": val}).dropna()
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
