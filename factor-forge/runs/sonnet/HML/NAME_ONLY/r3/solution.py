import pandas as pd
import numpy as np

rows = []
started = False
with open("6_Portfolios_2x3.csv", "r", encoding="latin-1") as f:
    in_section = False
    for line in f:
        s = line.strip()
        if not in_section:
            if "Average Value Weighted Returns" in s and "Monthly" in s:
                in_section = True
            continue
        if not s:
            if started:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts[0]) == 6 and parts[0].isdigit():
            started = True
            if len(parts) >= 7:
                rows.append(parts[:7])
        else:
            if started:
                break

df = pd.DataFrame(rows, columns=["date", "SL", "M2", "SH", "BL", "M5", "BH"])
df["date"] = df["date"].astype(int)
for c in ["SL", "M2", "SH", "BL", "M5", "BH"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c] <= -99.99, c] = np.nan
df["value"] = (df["SH"] + df["BH"]) / 2 - (df["SL"] + df["BL"]) / 2
out = df[["date", "value"]].dropna()
out.to_csv("output.csv", index=False)
