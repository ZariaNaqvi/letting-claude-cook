import re
import pandas as pd
import numpy as np

rows = []
started = False
with open("6_Portfolios_ME_Prior_1_0.csv", "r", errors="ignore") as f:
    for line in f:
        parts = [p.strip() for p in line.strip().split(",")]
        if parts and re.fullmatch(r"\d{6}", parts[0]) and len(parts) >= 7:
            started = True
            rows.append(parts[:7])
        elif started:
            break

df = pd.DataFrame(rows, columns=["date", "SL", "SM", "SH", "BL", "BM", "BH"])
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c] <= -99.0, c] = np.nan

df["value"] = 0.5 * (df["SL"] + df["BL"]) - 0.5 * (df["SH"] + df["BH"])
out = df[["date", "value"]].dropna()
out.to_csv("output.csv", index=False)
