import pandas as pd
import numpy as np

rows = []
started = False
with open("6_Portfolios_ME_Prior_12_2.csv", "r", encoding="latin-1") as f:
    for line in f:
        s = line.strip()
        if not started:
            if "SMALL LoPRIOR" in s:
                header = [h.strip() for h in s.split(",")]
                started = True
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts) >= 7 and parts[0].isdigit() and len(parts[0]) == 6:
            rows.append(parts[:7])
        else:
            if rows:
                break
            else:
                continue

cols = ["date"] + header[1:7]
df = pd.DataFrame(rows, columns=cols)
df["date"] = df["date"].astype(int)
for c in cols[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c] <= -99.0, c] = np.nan

val = 0.5 * (df["SMALL HiPRIOR"] + df["BIG HiPRIOR"]) - 0.5 * (df["SMALL LoPRIOR"] + df["BIG LoPRIOR"])
out = pd.DataFrame({"date": df["date"], "value": val}).dropna()
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
