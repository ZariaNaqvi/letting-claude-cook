import csv
import pandas as pd

rows = []
header = None
started = False
with open("6_Portfolios_ME_OP_2x3.csv", newline="") as f:
    for line in f:
        s = line.strip()
        if not started:
            if "Value Weighted" in s and "Monthly" in s:
                started = True
            continue
        if header is None:
            if s.startswith(",") or "LoOP" in s:
                header = [h.strip() for h in next(csv.reader([s]))]
            continue
        parts = [p.strip() for p in next(csv.reader([s]))] if s else []
        if parts and len(parts[0]) == 6 and parts[0].isdigit():
            rows.append(parts)
        else:
            break

cols = ["date"] + header[1:]
df = pd.DataFrame([r[:len(cols)] for r in rows], columns=cols)
for c in cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")
need = ["SMALL LoOP", "SMALL HiOP", "BIG LoOP", "BIG HiOP"]
for c in need:
    df.loc[df[c].isin([-99.99, -999]), c] = float("nan")
df = df.dropna(subset=need)
df["value"] = 0.5 * (df["SMALL HiOP"] + df["BIG HiOP"]) - 0.5 * (df["SMALL LoOP"] + df["BIG LoOP"])
out = df[["date", "value"]].copy()
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
