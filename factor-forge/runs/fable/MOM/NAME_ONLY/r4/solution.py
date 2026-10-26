import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_Prior_12_2.csv"

with open(fname, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the first monthly value-weighted table: header line starting with a comma
rows = []
in_table = False
for line in lines:
    s = line.strip()
    if not in_table:
        if s.startswith(",") and "LoPRIOR" in s.upper():
            in_table = True
        continue
    # inside table
    if s == "":
        if rows:
            break
        continue
    parts = [p.strip() for p in s.split(",")]
    if not re.fullmatch(r"\d{6}", parts[0]):
        # end of monthly block (e.g., annual header)
        if rows:
            break
        continue
    try:
        vals = [float(x) for x in parts[1:7]]
    except ValueError:
        continue
    if len(vals) != 6:
        continue
    rows.append([int(parts[0])] + vals)

df = pd.DataFrame(rows, columns=["date", "SL", "SM", "SH", "BL", "BM", "BH"])
# mark missing
for c in ["SL", "SM", "SH", "BL", "BM", "BH"]:
    df.loc[df[c].isin([-99.99, -999.0]), c] = np.nan

df["value"] = 0.5 * (df["SH"] + df["BH"]) - 0.5 * (df["SL"] + df["BL"])
df = df.dropna(subset=["value"])
df["value"] = df["value"].round(2)
df = df.sort_values("date").drop_duplicates("date")
df[["date", "value"]].to_csv("output.csv", index=False)
