import pandas as pd
import numpy as np

rows = []
started = False
with open("6_Portfolios_ME_Prior_12_2.csv") as f:
    for line in f:
        parts = [p.strip() for p in line.strip().split(",")]
        is_data = len(parts) >= 7 and len(parts[0]) == 6 and parts[0].isdigit()
        if is_data:
            started = True
            rows.append(parts[:7])
        elif started:
            break

df = pd.DataFrame(rows, columns=["date", "sl", "sm", "sh", "bl", "bm", "bh"])
df["date"] = df["date"].astype(int)
for c in ["sl", "sm", "sh", "bl", "bm", "bh"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c] <= -99.0, c] = np.nan
df = df.dropna()
df["value"] = (df["sh"] + df["bh"]) / 2 - (df["sl"] + df["bl"]) / 2
df[["date", "value"]].round(4).to_csv("output.csv", index=False)
