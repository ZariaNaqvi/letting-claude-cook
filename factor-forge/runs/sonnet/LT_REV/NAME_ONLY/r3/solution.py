import pandas as pd
import numpy as np

rows = []
started = False
seen = False
with open("6_Portfolios_ME_Prior_60_13.csv", "r", errors="ignore") as f:
    for line in f:
        s = line.strip()
        if not started:
            if "Average Value Weighted Returns" in s and "Monthly" in s:
                started = True
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts) >= 7 and parts[0].isdigit() and len(parts[0]) == 6:
            seen = True
            try:
                vals = [float(x) for x in parts[1:7]]
            except ValueError:
                continue
            rows.append([int(parts[0])] + vals)
        else:
            if seen:
                break

df = pd.DataFrame(rows, columns=["date", "sl", "sm", "sh", "bl", "bm", "bh"])
v = df[["sl", "sm", "sh", "bl", "bm", "bh"]].copy()
bad = (v <= -99.0).any(axis=1)
val = 0.5 * (df["sl"] + df["bl"]) - 0.5 * (df["sh"] + df["bh"])
val[bad] = np.nan
out = pd.DataFrame({"date": df["date"].astype(int), "value": val})
out = out.dropna().reset_index(drop=True)
out.to_csv("output.csv", index=False)
