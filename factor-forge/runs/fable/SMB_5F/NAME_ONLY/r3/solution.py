import pandas as pd
import numpy as np

def read_monthly_vw(fname):
    with open(fname, "r") as f:
        lines = f.read().splitlines()
    start = None
    for i, line in enumerate(lines):
        if "Average Value Weighted Returns" in line and "Monthly" in line:
            start = i
            break
    if start is None:
        raise ValueError("Monthly VW block not found in " + fname)
    rows = []
    for line in lines[start + 2:]:
        s = line.strip()
        if s == "":
            if rows:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        d = parts[0]
        if len(d) != 6 or not d.isdigit():
            if rows:
                break
            continue
        vals = []
        for p in parts[1:7]:
            try:
                v = float(p)
            except ValueError:
                v = np.nan
            if v <= -99.0:
                v = np.nan
            vals.append(v)
        rows.append([int(d)] + vals)
    df = pd.DataFrame(rows, columns=["date", "SL", "SM", "SH", "BL", "BM", "BH"])
    df = df.set_index("date")
    return df

def smb_component(df):
    small = (df["SL"] + df["SM"] + df["SH"]) / 3.0
    big = (df["BL"] + df["BM"] + df["BH"]) / 3.0
    return small - big

bm = read_monthly_vw("6_Portfolios_2x3.csv")
op = read_monthly_vw("6_Portfolios_ME_OP_2x3.csv")
inv = read_monthly_vw("6_Portfolios_ME_INV_2x3.csv")

s_bm = smb_component(bm)
s_op = smb_component(op)
s_inv = smb_component(inv)

combined = pd.concat([s_bm.rename("bm"), s_op.rename("op"), s_inv.rename("inv")], axis=1, join="inner")
combined = combined.dropna()
smb = (combined["bm"] + combined["op"] + combined["inv"]) / 3.0

out = pd.DataFrame({"date": smb.index.astype(int), "value": smb.values.round(4)})
out = out.sort_values("date").reset_index(drop=True)
out.to_csv("output.csv", index=False)
