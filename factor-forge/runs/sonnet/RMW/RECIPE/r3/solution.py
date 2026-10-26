import pandas as pd
import numpy as np

rows = []
cols = None
started = False
with open("6_Portfolios_ME_OP_2x3.csv", "r", encoding="latin-1") as f:
    for line in f:
        s = line.strip()
        if not started:
            if s.startswith("Average Value Weighted Returns") and "Monthly" in s:
                started = True
            continue
        if cols is None:
            if s.startswith(","):
                cols = [c.strip() for c in s.split(",")[1:]]
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts) >= 7 and parts[0].isdigit() and len(parts[0]) == 6:
            rows.append([int(parts[0])] + [float(x) for x in parts[1:1 + len(cols)]])
        else:
            if rows:
                break

df = pd.DataFrame(rows, columns=["date"] + cols)
df = df.replace([-99.99, -999, -999.0], np.nan)
val = 0.5 * (df["SMALL HiOP"] + df["BIG HiOP"]) - 0.5 * (df["SMALL LoOP"] + df["BIG LoOP"])
out = pd.DataFrame({"date": df["date"].astype(int), "value": val}).dropna()
out.to_csv("output.csv", index=False)
