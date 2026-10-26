import pandas as pd
import numpy as np

rows = []
started = False
with open("6_Portfolios_ME_INV_2x3.csv", "r", errors="ignore") as f:
    for line in f:
        s = line.strip()
        if not started:
            if "Average Value Weighted Returns" in s and "Monthly" in s:
                started = True
            continue
        if not s:
            if rows:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts) >= 7 and parts[0].isdigit() and len(parts[0]) == 6:
            try:
                vals = [float(x) for x in parts[1:7]]
            except ValueError:
                continue
            rows.append([int(parts[0])] + vals)
        else:
            if rows:
                break

df = pd.DataFrame(rows, columns=["date", "c0", "c1", "c2", "c3", "c4", "c5"])
for c in ["c0", "c1", "c2", "c3", "c4", "c5"]:
    df[c] = df[c].where(~df[c].isin([-99.99, -999.0]), np.nan)
df["value"] = 0.5 * (df["c0"] + df["c3"]) - 0.5 * (df["c2"] + df["c5"])
out = df.dropna(subset=["value"])[["date", "value"]].copy()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
