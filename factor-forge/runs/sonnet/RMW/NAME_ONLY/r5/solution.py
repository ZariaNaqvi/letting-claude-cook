import pandas as pd
import numpy as np

rows = []
started = False
in_section = False
with open("6_Portfolios_ME_OP_2x3.csv") as f:
    for line in f:
        s = line.strip()
        if not in_section:
            if "Value Weighted Returns" in s and "Monthly" in s:
                in_section = True
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts) >= 7 and len(parts[0]) == 6 and parts[0].isdigit():
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
    df.loc[df[c] <= -99.0, c] = np.nan
df["value"] = (df["sh"] + df["bh"]) / 2 - (df["sl"] + df["bl"]) / 2
out = df[["date", "value"]].dropna()
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
