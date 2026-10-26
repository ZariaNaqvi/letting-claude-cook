import csv
import numpy as np
import pandas as pd

rows = []
started = False
with open("6_Portfolios_2x3.csv", newline="") as f:
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
        parts = [p.strip() for p in next(csv.reader([s]))]
        if parts[0].isdigit() and len(parts[0]) == 6:
            try:
                rows.append([int(parts[0])] + [float(x) for x in parts[1:7]])
            except ValueError:
                break
        else:
            if rows:
                break

df = pd.DataFrame(rows, columns=["date", "a", "b", "c", "d", "e", "f"])
vals = df[["a", "b", "c", "d", "e", "f"]].astype(float)
vals = vals.where(~vals.isin([-99.99, -999.0]), np.nan)
small = vals[["a", "b", "c"]].sum(axis=1, skipna=False) / 3
big = vals[["d", "e", "f"]].sum(axis=1, skipna=False) / 3
out = pd.DataFrame({"date": df["date"].astype(int), "value": small - big})
out = out.dropna().reset_index(drop=True)
out.to_csv("output.csv", index=False)
