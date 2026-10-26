import pandas as pd
import numpy as np

rows = []
started = False
in_section = False
with open("6_Portfolios_ME_Prior_1_0.csv", "r") as f:
    for line in f:
        s = line.strip()
        if not in_section:
            if "Value Weighted Returns" in s and "Monthly" in s:
                in_section = True
            continue
        if not s:
            if started:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts[0]) == 6 and parts[0].isdigit() and len(parts) >= 7:
            started = True
            try:
                vals = [float(x) for x in parts[1:7]]
            except ValueError:
                continue
            rows.append([int(parts[0])] + vals)
        elif started:
            break

df = pd.DataFrame(rows, columns=["date", "sl", "sm", "sh", "bl", "bm", "bh"])
for c in ["sl", "sm", "sh", "bl", "bm", "bh"]:
    df.loc[(df[c] <= -99.99) | (df[c] <= -999), c] = np.nan
df["value"] = 0.5 * (df["sl"] + df["bl"]) - 0.5 * (df["sh"] + df["bh"])
out = df.dropna(subset=["value"])[["date", "value"]].copy()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
