import pandas as pd
import numpy as np

rows = []
header = None
started = False
in_block = False
with open("6_Portfolios_ME_Prior_1_0.csv", "r", errors="replace") as f:
    for line in f:
        s = line.strip()
        if not in_block:
            if "Average Value Weighted Returns" in s and "Monthly" in s:
                in_block = True
            continue
        if header is None:
            if s.startswith(","):
                header = [h.strip().upper() for h in s.split(",")]
            continue
        parts = [p.strip() for p in s.split(",")]
        if parts and len(parts[0]) == 6 and parts[0].isdigit():
            started = True
            rows.append(parts)
        else:
            if started:
                break

cols = header[1:]
df = pd.DataFrame(rows)
df = df.iloc[:, :len(cols) + 1]
df.columns = ["date"] + cols
df["date"] = df["date"].astype(int)
for c in cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c].isin([-99.99, -999, -999.0]), c] = np.nan

df["value"] = 0.5 * (df["SMALL LOPRIOR"] + df["BIG LOPRIOR"]) - 0.5 * (df["SMALL HIPRIOR"] + df["BIG HIPRIOR"])
out = df[["date", "value"]].dropna()
out.to_csv("output.csv", index=False)
