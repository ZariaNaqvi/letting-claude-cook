import csv
import numpy as np
import pandas as pd

rows = []
in_block = False
started = False
with open("6_Portfolios_2x3.csv", "r", encoding="latin-1") as f:
    for line in f:
        s = line.strip()
        if not in_block:
            if "Average Value Weighted Returns" in s and "Monthly" in s:
                in_block = True
            continue
        if not s:
            if started:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if not started:
            if parts[0] == "" and len(parts) >= 7:
                started = True  # header line
                continue
            continue
        if len(parts[0]) == 6 and parts[0].isdigit() and len(parts) >= 7:
            rows.append([int(parts[0])] + [float(x) for x in parts[1:7]])
        else:
            break

df = pd.DataFrame(rows, columns=["date", "a", "b", "c", "d", "e", "f"])
vals = df[["a", "b", "c", "d", "e", "f"]].astype(float)
vals = vals.mask((vals <= -99.99) | (vals == -999))
small = vals[["a", "b", "c"]].mean(axis=1, skipna=False)
big = vals[["d", "e", "f"]].mean(axis=1, skipna=False)
out = pd.DataFrame({"date": df["date"].astype(int), "value": small - big})
out = out.dropna().reset_index(drop=True)
out.to_csv("output.csv", index=False)
