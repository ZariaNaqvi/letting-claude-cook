import pandas as pd
import numpy as np
import re

def read_monthly_vw(fname):
    with open(fname, "r") as f:
        lines = f.read().splitlines()
    # locate the first "Average Value Weighted Returns -- Monthly" section
    start = None
    for i, line in enumerate(lines):
        if "Average Value Weighted Returns" in line and "Monthly" in line:
            start = i
            break
    if start is None:
        raise ValueError("Monthly VW section not found in " + fname)
    rows = []
    for line in lines[start + 1:]:
        s = line.strip()
        if s == "":
            if rows:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if re.fullmatch(r"\d{6}", parts[0]):
            vals = []
            for p in parts[1:]:
                try:
                    v = float(p)
                except ValueError:
                    v = np.nan
                if v <= -99.0:
                    v = np.nan
                vals.append(v)
            if len(vals) >= 6:
                rows.append([int(parts[0])] + vals[:6])
        elif rows:
            break
    df = pd.DataFrame(rows, columns=["date", "SL", "SM", "SH", "BL", "BM", "BH"])
    df = df.drop_duplicates("date").set_index("date").sort_index()
    return df

def smb_component(df):
    small = (df["SL"] + df["SM"] + df["SH"]) / 3.0
    big = (df["BL"] + df["BM"] + df["BH"]) / 3.0
    return small - big

bm = read_monthly_vw("6_Portfolios_2x3.csv")
op = read_monthly_vw("6_Portfolios_ME_OP_2x3.csv")
inv = read_monthly_vw("6_Portfolios_ME_INV_2x3.csv")

smb_bm = smb_component(bm)
smb_op = smb_component(op)
smb_inv = smb_component(inv)

common = smb_bm.index.intersection(smb_op.index).intersection(smb_inv.index)
smb = (smb_bm.loc[common] + smb_op.loc[common] + smb_inv.loc[common]) / 3.0
smb = smb.dropna()

out = pd.DataFrame({"date": smb.index.astype(int), "value": smb.values.round(4)})
out = out.sort_values("date").reset_index(drop=True)
out.to_csv("output.csv", index=False)
