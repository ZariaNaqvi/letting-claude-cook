import re
import numpy as np
import pandas as pd

rows = []
started = False
with open("6_Portfolios_2x3.csv", "r", errors="ignore") as f:
    for line in f:
        s = line.strip()
        if not started:
            if s.startswith("Average Value Weighted Returns") and "Monthly" in s:
                started = True
            continue
        if not s:
            if rows:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if re.fullmatch(r"\d{6}", parts[0]) and len(parts) >= 7:
            rows.append(parts[:7])
        elif rows:
            break

df = pd.DataFrame(rows, columns=["date", "sl", "sm", "sh", "bl", "bm", "bh"])
df["date"] = df["date"].astype(int)
cols = ["sl", "sm", "sh", "bl", "bm", "bh"]
for c in cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df[cols] = df[cols].mask((df[cols] <= -99.0))
df = df.dropna()
df["value"] = (df["sl"] + df["sm"] + df["sh"]) / 3.0 - (df["bl"] + df["bm"] + df["bh"]) / 3.0
df[["date", "value"]].to_csv("output.csv", index=False)
