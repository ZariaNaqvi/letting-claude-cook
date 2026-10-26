import re
import numpy as np
import pandas as pd

rows = []
started = False
with open("6_Portfolios_ME_Prior_12_2.csv", "r", errors="ignore") as f:
    for line in f:
        s = line.strip()
        if not started:
            if "Value Weighted Returns" in s and "Monthly" in s:
                started = True
            continue
        if re.match(r"^\d{6}\s*,", s):
            parts = [p.strip() for p in s.split(",")]
            rows.append([int(parts[0])] + [float(x) for x in parts[1:7]])
        elif rows:
            break

df = pd.DataFrame(rows, columns=["date", "sl", "sm", "sh", "bl", "bm", "bh"])
for c in ["sl", "sm", "sh", "bl", "bm", "bh"]:
    df.loc[(df[c] <= -99.0), c] = np.nan
df["value"] = 0.5 * (df["sh"] + df["bh"]) - 0.5 * (df["sl"] + df["bl"])
out = df.dropna(subset=["value"])[["date", "value"]].copy()
out["value"] = out["value"].round(4)
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
