import re
import numpy as np
import pandas as pd

def read_vw_monthly(fname):
    with open(fname, "r", encoding="latin-1") as f:
        lines = f.read().splitlines()
    start = None
    for i, l in enumerate(lines):
        if "Average Value Weighted Returns -- Monthly" in l:
            start = i
            break
    if start is None:
        raise ValueError("VW monthly section not found in " + fname)
    header = [h.strip() for h in lines[start + 1].split(",")]
    rows = []
    for l in lines[start + 2:]:
        s = l.strip()
        if not s:
            break
        parts = [p.strip() for p in s.split(",")]
        if not re.fullmatch(r"\d{6}", parts[0]):
            break
        rows.append([int(parts[0])] + [float(p) for p in parts[1:7]])
    cols = ["date"] + header[1:7]
    df = pd.DataFrame(rows, columns=cols).set_index("date")
    df = df.mask((df <= -99.99 + 1e-9) & (df >= -99.99 - 1e-9))
    df = df.mask(df <= -999 + 1e-9)
    return df

def smb_from(df):
    small = df.iloc[:, 0:3].mean(axis=1, skipna=False)
    big = df.iloc[:, 3:6].mean(axis=1, skipna=False)
    return small - big

bm = read_vw_monthly("6_Portfolios_2x3.csv")
op = read_vw_monthly("6_Portfolios_ME_OP_2x3.csv")
inv = read_vw_monthly("6_Portfolios_ME_INV_2x3.csv")

s = pd.concat([smb_from(bm), smb_from(op), smb_from(inv)], axis=1, join="inner")
smb = s.mean(axis=1, skipna=False).dropna()

out = pd.DataFrame({"date": smb.index.astype(int), "value": smb.values.round(6)})
out = out.sort_values("date")
out.to_csv("output.csv", index=False)
