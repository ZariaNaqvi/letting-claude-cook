import pandas as pd
import numpy as np

rows = []
started = False
with open("6_Portfolios_ME_Prior_60_13.csv", "r", errors="ignore") as f:
    in_section = False
    for line in f:
        s = line.strip()
        if not in_section:
            if s.startswith("Average Value Weighted Returns") and "Monthly" in s:
                in_section = True
            continue
        if not s:
            if started:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if parts[0].isdigit() and len(parts[0]) == 6:
            started = True
            rows.append(parts[:7])
        else:
            if started:
                break

df = pd.DataFrame(rows, columns=["date", "sl", "sm", "sh", "bl", "bm", "bh"])
df["date"] = df["date"].astype(int)
for c in ["sl", "sm", "sh", "bl", "bm", "bh"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c] <= -99.99, c] = np.nan

df["value"] = 0.5 * (df["sl"] + df["bl"]) - 0.5 * (df["sh"] + df["bh"])
out = df[["date", "value"]].dropna()
out.to_csv("output.csv", index=False)
