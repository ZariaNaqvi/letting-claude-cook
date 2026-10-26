import pandas as pd
import numpy as np

rows = []
header = None
started = False
with open("6_Portfolios_ME_Prior_1_0.csv", "r", errors="ignore") as f:
    for line in f:
        s = line.strip()
        if not started:
            if "Average Value Weighted Returns" in s and "Monthly" in s:
                started = True
            continue
        if header is None:
            if s.startswith(","):
                header = [h.strip() for h in s.split(",")]
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts) >= 2 and len(parts[0]) == 6 and parts[0].isdigit():
            rows.append(parts)
        else:
            if rows:
                break

cols = ["date"] + header[1:]
df = pd.DataFrame([r[:len(cols)] for r in rows], columns=cols)
df["date"] = df["date"].astype(int)
for c in cols[1:]:
    v = pd.to_numeric(df[c], errors="coerce")
    v = v.where(~v.isin([-99.99, -999, -999.0]))
    df[c] = v

val = 0.5 * (df["SMALL LoPRIOR"] + df["BIG LoPRIOR"]) - 0.5 * (df["SMALL HiPRIOR"] + df["BIG HiPRIOR"])
out = pd.DataFrame({"date": df["date"], "value": val}).dropna()
out.to_csv("output.csv", index=False)
