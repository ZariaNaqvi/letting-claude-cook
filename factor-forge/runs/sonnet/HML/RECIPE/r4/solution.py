import numpy as np
import pandas as pd

fn = "6_Portfolios_2x3.csv"
with open(fn, "r", encoding="latin-1") as f:
    lines = f.read().splitlines()

start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break

header = [h.strip() for h in lines[start + 1].split(",")]
rows = []
for l in lines[start + 2:]:
    parts = [p.strip() for p in l.split(",")]
    if len(parts) < 7 or not (parts[0].isdigit() and len(parts[0]) == 6):
        break
    rows.append(parts[:len(header)])

df = pd.DataFrame(rows, columns=["date"] + header[1:])
df["date"] = df["date"].astype(int)
for c in header[1:]:
    v = pd.to_numeric(df[c], errors="coerce")
    v = v.where(~v.isin([-99.99, -999, -999.0]))
    df[c] = v

val = 0.5 * (df["SMALL HiBM"] + df["BIG HiBM"]) - 0.5 * (df["SMALL LoBM"] + df["BIG LoBM"])
out = pd.DataFrame({"date": df["date"], "value": val}).dropna()
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
