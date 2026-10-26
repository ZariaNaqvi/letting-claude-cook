import csv
import pandas as pd

rows = []
header = None
started = False
with open("6_Portfolios_ME_Prior_1_0.csv", newline="") as f:
    for line in f:
        s = line.strip()
        if header is None:
            if "SMALL LoPRIOR" in s:
                header = [c.strip() for c in s.split(",")]
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts[0]) == 6 and parts[0].isdigit() and len(parts) >= len(header):
            started = True
            rows.append(parts[:len(header)])
        else:
            if started:
                break

header[0] = "date"
df = pd.DataFrame(rows, columns=header)
df["date"] = df["date"].astype(int)
cols = ["SMALL LoPRIOR", "BIG LoPRIOR", "SMALL HiPRIOR", "BIG HiPRIOR"]
for c in cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c].isin([-99.99, -999, -999.0]), c] = float("nan")
df = df.dropna(subset=cols)
df["value"] = 0.5 * (df["SMALL LoPRIOR"] + df["BIG LoPRIOR"]) - 0.5 * (df["SMALL HiPRIOR"] + df["BIG HiPRIOR"])
df[["date", "value"]].to_csv("output.csv", index=False)
