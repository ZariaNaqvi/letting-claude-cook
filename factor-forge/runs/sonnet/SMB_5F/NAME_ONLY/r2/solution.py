import re
import pandas as pd
import numpy as np


def read_first_block(fn):
    rows = {}
    started = False
    with open(fn, "r", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not started:
                if "Average Value Weighted Returns" in s and "Monthly" in s:
                    started = True
                continue
            if re.match(r"^\d{6}\s*,", s):
                parts = [p.strip() for p in s.split(",")]
                vals = []
                for p in parts[1:7]:
                    try:
                        v = float(p)
                    except ValueError:
                        v = np.nan
                    if v <= -99.0:
                        v = np.nan
                    vals.append(v)
                if len(vals) == 6:
                    rows[int(parts[0])] = vals
            else:
                if rows and s == "":
                    break
                if rows:
                    break
    df = pd.DataFrame.from_dict(rows, orient="index")
    return df


files = ["6_Portfolios_2x3.csv", "6_Portfolios_ME_OP_2x3.csv", "6_Portfolios_ME_INV_2x3.csv"]
smbs = []
for fn in files:
    d = read_first_block(fn)
    s = d[[0, 1, 2]].mean(axis=1, skipna=False) - d[[3, 4, 5]].mean(axis=1, skipna=False)
    smbs.append(s)

all_df = pd.concat(smbs, axis=1, join="inner")
res = all_df.mean(axis=1, skipna=False).dropna()
out = pd.DataFrame({"date": res.index.astype(int), "value": res.values})
out = out.sort_values("date")
out.to_csv("output.csv", index=False)
