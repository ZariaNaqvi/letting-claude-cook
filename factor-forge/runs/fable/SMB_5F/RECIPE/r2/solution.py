import pandas as pd
import numpy as np
import re

def read_first_monthly_block(fname):
    with open(fname, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    # locate first "Average Value Weighted Returns -- Monthly" header
    start = None
    for i, ln in enumerate(lines):
        if "Average Value Weighted Returns" in ln and "Monthly" in ln:
            start = i
            break
    if start is None:
        # fallback: first line starting with a 6-digit YYYYMM
        for i, ln in enumerate(lines):
            if re.match(r"^\s*\d{6}\s*,", ln):
                start = i - 1
                break
    # header line is the next line containing commas
    j = start + 1
    while j < len(lines) and "," not in lines[j]:
        j += 1
    header = [h.strip() for h in lines[j].split(",")]
    cols = header[1:]
    rows = []
    k = j + 1
    while k < len(lines):
        ln = lines[k]
        if not ln.strip():
            # blank line ends block (only if we already have rows)
            if rows:
                break
            k += 1
            continue
        m = re.match(r"^\s*(\d{6})\s*,(.*)$", ln)
        if not m:
            if rows:
                break
            k += 1
            continue
        date = int(m.group(1))
        vals = [v.strip() for v in m.group(2).split(",")]
        try:
            vals = [float(v) for v in vals[:len(cols)]]
        except ValueError:
            break
        if len(vals) != len(cols):
            break
        rows.append([date] + vals)
        k += 1
    df = pd.DataFrame(rows, columns=["date"] + cols)
    df = df.set_index("date")
    df = df.replace([-99.99, -999.0], np.nan)
    return df

def smb_component(df):
    cols = list(df.columns)
    small = [c for c in cols if c.upper().startswith("SMALL") or c.upper().startswith("ME1 ")]
    big = [c for c in cols if c.upper().startswith("BIG") or c.upper().startswith("ME2 ")]
    if len(small) != 3 or len(big) != 3:
        # fallback to positional: first 3 small, last 3 big
        small = cols[:3]
        big = cols[3:6]
    return df[small].mean(axis=1) - df[big].mean(axis=1)

bm = read_first_monthly_block("6_Portfolios_2x3.csv")
op = read_first_monthly_block("6_Portfolios_ME_OP_2x3.csv")
inv = read_first_monthly_block("6_Portfolios_ME_INV_2x3.csv")

s_bm = smb_component(bm)
s_op = smb_component(op)
s_inv = smb_component(inv)

common = s_bm.index.intersection(s_op.index).intersection(s_inv.index)
common = sorted(common)
smb = (s_bm.loc[common] + s_op.loc[common] + s_inv.loc[common]) / 3.0

out = pd.DataFrame({"date": [int(d) for d in common], "value": smb.values})
out = out.dropna()
out["date"] = out["date"].astype(int)
out = out.sort_values("date").reset_index(drop=True)
out.to_csv("output.csv", index=False)
