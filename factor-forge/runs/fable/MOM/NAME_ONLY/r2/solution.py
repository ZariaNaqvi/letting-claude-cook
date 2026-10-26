import pandas as pd
import numpy as np
import re

fname = "6_Portfolios_ME_Prior_12_2.csv"

with open(fname, "r") as f:
    lines = f.readlines()

# Locate the first monthly section (value-weighted returns): header line beginning with a comma,
# followed by rows whose first field is a 6-digit YYYYMM date.
rows = []
in_section = False
for line in lines:
    s = line.strip()
    if not in_section:
        if s.startswith(",") and "LoPRIOR" in s.upper():
            in_section = True
        continue
    # in section
    if s == "":
        if rows:
            break
        continue
    parts = [p.strip() for p in s.split(",")]
    if re.fullmatch(r"\d{6}", parts[0]) and len(parts) >= 7:
        try:
            vals = [float(x) for x in parts[1:7]]
        except ValueError:
            break
        rows.append([int(parts[0])] + vals)
    else:
        if rows:
            break

cols = ["date", "SL", "SM", "SH", "BL", "BM", "BH"]
df = pd.DataFrame(rows, columns=cols)

# Treat missing codes as NaN
for c in cols[1:]:
    df.loc[df[c] <= -99.99, c] = np.nan

df["value"] = 0.5 * (df["SH"] + df["BH"]) - 0.5 * (df["SL"] + df["BL"])
out = df[["date", "value"]].dropna()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
