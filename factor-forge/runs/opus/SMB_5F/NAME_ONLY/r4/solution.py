import pandas as pd
import numpy as np

def read_vw_monthly(fname):
    with open(fname, "r", encoding="latin-1") as f:
        lines = f.read().splitlines()
    start = None
    for i, l in enumerate(lines):
        if "Average Value Weighted Returns -- Monthly" in l:
            start = i
            break
    if start is None:
        raise ValueError("block not found in " + fname)
    header = [h.strip() for h in lines[start + 1].split(",")]
    rows = []
    for l in lines[start + 2:]:
        parts = [p.strip() for p in l.split(",")]
        if len(parts) < 7 or not (parts[0].isdigit() and len(parts[0]) == 6):
            break
        rows.append([int(parts[0])] + [float(x) for x in parts[1:7]])
    df = pd.DataFrame(rows, columns=["date"] + header[1:7]).set_index("date")
    df = df.replace([-99.99, -999.0], np.nan)
    return df

def smb_component(df):
    cols = list(df.columns)
    small = df[cols[0:3]].mean(axis=1, skipna=False)
    big = df[cols[3:6]].mean(axis=1, skipna=False)
    return small - big

bm = read_vw_monthly("6_Portfolios_2x3.csv")
op = read_vw_monthly("6_Portfolios_ME_OP_2x3.csv")
inv = read_vw_monthly("6_Portfolios_ME_INV_2x3.csv")

s = pd.concat([smb_component(bm), smb_component(op), smb_component(inv)],
              axis=1, join="inner")
s = s.dropna()
smb = s.mean(axis=1)

out = pd.DataFrame({"date": smb.index.astype(int), "value": smb.values.round(6)})
out = out.sort_values("date")
out.to_csv("output.csv", index=False)
