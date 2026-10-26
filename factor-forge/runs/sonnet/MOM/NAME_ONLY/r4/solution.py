import re
import pandas as pd
import numpy as np

rows = []
started = False
with open("6_Portfolios_ME_Prior_12_2.csv", "r", errors="ignore") as f:
    for line in f:
        s = line.strip()
        if not started:
            if "Value Weighted Returns" in s and "Monthly" in s:
                started = True
            continue
        if not s:
            if rows:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if re.fullmatch(r"\d{6}", parts[0]) and len(parts) >= 7:
            try:
                vals = [float(x) for x in parts[1:7]]
            except ValueError:
                continue
            rows.append([int(parts[0])] + vals)
        else:
            if rows:
                break

df = pd.DataFrame(rows, columns=["date", "sl", "sm", "sh", "bl", "bm", "bh"])
vals = df[["sl", "sm", "sh", "bl", "bm", "bh"]].copy()
vals = vals.mask((vals <= -99.99) | (vals <= -999))
df[["sl", "sm", "sh", "bl", "bm", "bh"]] = vals
df = df.dropna()
df["value"] = (0.5 * (df["sh"] + df["bh"]) - 0.5 * (df["sl"] + df["bl"])).round(2)
df[["date", "value"]].to_csv("output.csv", index=False)
