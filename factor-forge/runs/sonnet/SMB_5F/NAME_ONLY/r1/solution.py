import pandas as pd
import numpy as np


def read_first_section(fn):
    with open(fn, "r", errors="ignore") as f:
        lines = f.read().splitlines()
    start = None
    for i, l in enumerate(lines):
        if "Value Weighted Returns" in l and "Monthly" in l:
            start = i + 2
            break
    rows = {}
    started = False
    for l in lines[start:]:
        parts = [p.strip() for p in l.split(",")]
        if parts and len(parts[0]) == 6 and parts[0].isdigit() and len(parts) >= 7:
            started = True
            vals = [float(x) for x in parts[1:7]]
            vals = [np.nan if (v <= -99.99) else v for v in vals]
            rows[int(parts[0])] = vals
        elif started:
            break
    df = pd.DataFrame.from_dict(rows, orient="index")
    return df


def smb_part(df):
    return df.iloc[:, 0:3].mean(axis=1, skipna=False) - df.iloc[:, 3:6].mean(axis=1, skipna=False)


bm = read_first_section("6_Portfolios_2x3.csv")
op = read_first_section("6_Portfolios_ME_OP_2x3.csv")
inv = read_first_section("6_Portfolios_ME_INV_2x3.csv")

idx = bm.index.intersection(op.index).intersection(inv.index)
s = (smb_part(bm.loc[idx]) + smb_part(op.loc[idx]) + smb_part(inv.loc[idx])) / 3.0
s = s.dropna().sort_index()
out = pd.DataFrame({"date": s.index.astype(int), "value": s.values})
out.to_csv("output.csv", index=False)
