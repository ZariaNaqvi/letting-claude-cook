import pandas as pd
import numpy as np


def read_first_section(fn):
    with open(fn, "r", errors="ignore") as f:
        lines = f.read().splitlines()
    start = None
    for i, l in enumerate(lines):
        if "Average Value Weighted Returns" in l and "Monthly" in l:
            start = i + 1
            break
    rows = {}
    for l in lines[start:]:
        parts = [p.strip() for p in l.split(",")]
        if parts and len(parts[0]) == 6 and parts[0].isdigit():
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
            if rows:
                break
    df = pd.DataFrame.from_dict(rows, orient="index")
    return df


def smb_part(df):
    return df[[0, 1, 2]].mean(axis=1, skipna=False) - df[[3, 4, 5]].mean(axis=1, skipna=False)


a = smb_part(read_first_section("6_Portfolios_2x3.csv"))
b = smb_part(read_first_section("6_Portfolios_ME_OP_2x3.csv"))
c = smb_part(read_first_section("6_Portfolios_ME_INV_2x3.csv"))

d = pd.concat([a, b, c], axis=1, join="inner").dropna()
smb = d.mean(axis=1)
out = pd.DataFrame({"date": smb.index.astype(int), "value": smb.values.round(4)})
out = out.sort_values("date")
out.to_csv("output.csv", index=False)
