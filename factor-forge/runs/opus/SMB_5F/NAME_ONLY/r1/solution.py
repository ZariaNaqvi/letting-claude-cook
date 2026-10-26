import pandas as pd
import numpy as np

def read_vw_monthly(fname):
    with open(fname, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    start = None
    for i, l in enumerate(lines):
        if "Value Weighted Returns" in l and "Monthly" in l:
            start = i
            break
    if start is None:
        raise ValueError("section not found in " + fname)
    header = [h.strip() for h in lines[start + 1].split(",")]
    rows = []
    for l in lines[start + 2:]:
        parts = [p.strip() for p in l.split(",")]
        if len(parts) < 7 or not (parts[0].isdigit() and len(parts[0]) == 6):
            break
        vals = []
        for p in parts[1:7]:
            try:
                v = float(p)
            except ValueError:
                v = np.nan
            if v <= -99.99 + 1e-9 or v == -999:
                v = np.nan
            vals.append(v)
        rows.append([int(parts[0])] + vals)
    df = pd.DataFrame(rows, columns=["date"] + header[1:7]).set_index("date")
    return df

def smb_from(df):
    small = df.iloc[:, 0:3].mean(axis=1, skipna=False)
    big = df.iloc[:, 3:6].mean(axis=1, skipna=False)
    return small - big

bm = smb_from(read_vw_monthly("6_Portfolios_2x3.csv"))
op = smb_from(read_vw_monthly("6_Portfolios_ME_OP_2x3.csv"))
inv = smb_from(read_vw_monthly("6_Portfolios_ME_INV_2x3.csv"))

combined = pd.concat([bm.rename("bm"), op.rename("op"), inv.rename("inv")], axis=1, join="inner")
combined = combined.dropna()
smb = (combined["bm"] + combined["op"] + combined["inv"]) / 3.0

out = pd.DataFrame({"date": smb.index.astype(int), "value": smb.values.round(6)})
out = out.sort_values("date")
out.to_csv("output.csv", index=False)
