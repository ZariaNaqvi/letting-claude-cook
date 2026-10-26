import pandas as pd
import numpy as np

rows = []
started = False
with open("6_Portfolios_2x3.csv", "r", encoding="latin-1") as f:
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
        if parts[0].isdigit() and len(parts[0]) == 6:
            rows.append(parts[:7])
        elif rows:
            break

df = pd.DataFrame(rows, columns=["date", "a", "b", "c", "d", "e", "f"])
df["date"] = df["date"].astype(int)
cols = ["a", "b", "c", "d", "e", "f"]
for c in cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df[cols] = df[cols].where(~df[cols].isin([-99.99, -999, -999.0]))
df["value"] = df[["a", "b", "c"]].mean(axis=1, skipna=False) - df[["d", "e", "f"]].mean(axis=1, skipna=False)
out = df[["date", "value"]].dropna()
out.to_csv("output.csv", index=False)
