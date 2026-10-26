import pandas as pd
import numpy as np

rows = []
started = False
with open("6_Portfolios_2x3.csv", "r") as f:
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
                rows.append([int(parts[0])] + [float(x) for x in parts[1:7]])
            except ValueError:
                pass
        elif rows:
            break

df = pd.DataFrame(rows, columns=["date", "sl", "sm", "sh", "bl", "bm", "bh"])
cols = ["sl", "sm", "sh", "bl", "bm", "bh"]
df[cols] = df[cols].mask((df[cols] <= -99.0))
df = df.dropna()
df["value"] = (df["sh"] + df["bh"]) / 2 - (df["sl"] + df["bl"]) / 2
df[["date", "value"]].to_csv("output.csv", index=False)
