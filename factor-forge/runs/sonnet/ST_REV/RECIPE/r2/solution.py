import numpy as np
import pandas as pd

fn = "6_Portfolios_ME_Prior_1_0.csv"
with open(fn, "r", errors="replace") as f:
    lines = f.read().splitlines()

hdr_idx = None
for i, l in enumerate(lines):
    if "SMALL LoPRIOR" in l:
        hdr_idx = i
        break

header = [h.strip() for h in lines[hdr_idx].split(",")]
rows = []
for l in lines[hdr_idx + 1:]:
    parts = [p.strip() for p in l.split(",")]
    if not parts or not parts[0]:
        if rows:
            break
        continue
    if not (parts[0].isdigit() and len(parts[0]) == 6):
        if rows:
            break
        continue
    rows.append(parts[:len(header)])

df = pd.DataFrame(rows, columns=header)
df.rename(columns={header[0]: "date"}, inplace=True)
df["date"] = df["date"].astype(int)
cols = ["SMALL LoPRIOR", "BIG LoPRIOR", "SMALL HiPRIOR", "BIG HiPRIOR"]
for c in cols + ["ME1 PRIOR2", "ME2 PRIOR2"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
for c in cols:
    df.loc[df[c] <= -99.0, c] = np.nan

df["value"] = 0.5 * (df["SMALL LoPRIOR"] + df["BIG LoPRIOR"]) - 0.5 * (df["SMALL HiPRIOR"] + df["BIG HiPRIOR"])
out = df[["date", "value"]].dropna()
out.to_csv("output.csv", index=False)
