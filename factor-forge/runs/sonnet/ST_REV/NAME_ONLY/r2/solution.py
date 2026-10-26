import re
import pandas as pd
import numpy as np

rows = []
started = False
with open("6_Portfolios_ME_Prior_1_0.csv", "r", errors="ignore") as f:
    for line in f:
        s = line.strip()
        if not started:
            if s.startswith(",") and "SMALL" in s.upper():
                started = True
            continue
        parts = [p.strip() for p in s.split(",")]
        if re.fullmatch(r"\d{6}", parts[0]) and len(parts) >= 7:
            rows.append(parts[:7])
        else:
            if rows:
                break
            if s == "":
                continue

df = pd.DataFrame(rows, columns=["date", "sl", "sm", "sh", "bl", "bm", "bh"])
df["date"] = df["date"].astype(int)
for c in ["sl", "sm", "sh", "bl", "bm", "bh"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c] <= -99.0, c] = np.nan
df["value"] = 0.5 * (df["sl"] + df["bl"]) - 0.5 * (df["sh"] + df["bh"])
out = df[["date", "value"]].dropna()
out["value"] = out["value"].round(6)
out.to_csv("output.csv", index=False)
