import re
import pandas as pd

rows = []
started = False
with open("6_Portfolios_ME_INV_2x3.csv", "r", errors="ignore") as f:
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
for c in ["sl", "sm", "sh", "bl", "bm", "bh"]:
    df.loc[df[c].isin([-99.99, -999.0]), c] = float("nan")
df["value"] = 0.5 * (df["sl"] + df["bl"]) - 0.5 * (df["sh"] + df["bh"])
out = df[["date", "value"]].dropna()
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
