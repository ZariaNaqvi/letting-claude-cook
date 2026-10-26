import pandas as pd
import numpy as np

rows = []
started = False
in_section = False
with open("6_Portfolios_ME_INV_2x3.csv", "r", errors="ignore") as f:
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
        if parts[0].isdigit() and len(parts[0]) == 6 and len(parts) >= 7:
            started = True
            rows.append([int(parts[0])] + [float(x) for x in parts[1:7]])
        else:
            if started:
                break

df = pd.DataFrame(rows, columns=["date", "SL", "SM", "SH", "BL", "BM", "BH"])
for c in ["SL", "SM", "SH", "BL", "BM", "BH"]:
    df.loc[df[c] <= -99.0, c] = np.nan
df["value"] = (df["SL"] + df["BL"]) / 2 - (df["SH"] + df["BH"]) / 2
out = df[["date", "value"]].dropna()
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
