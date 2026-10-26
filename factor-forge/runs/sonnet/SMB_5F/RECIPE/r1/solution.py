import pandas as pd
import numpy as np


def read_first_block(fn):
    rows = []
    started = False
    with open(fn, "r", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not started:
                if "Average Value Weighted Returns" in s and "Monthly" in s:
                    started = True
                continue
            if not s:
                if rows:
                    break
                continue
            parts = [p.strip() for p in s.split(",")]
            if parts[0].isdigit() and len(parts[0]) == 6 and len(parts) >= 7:
                vals = []
                for p in parts[1:7]:
                    try:
                        v = float(p)
                    except ValueError:
                        v = np.nan
                    if v <= -99.0:
                        v = np.nan
                    vals.append(v)
                rows.append([int(parts[0])] + vals)
            else:
                if rows:
                    break
    df = pd.DataFrame(rows, columns=["date", "s1", "s2", "s3", "b1", "b2", "b3"])
    return df


def smb(fn, name):
    df = read_first_block(fn)
    v = df[["s1", "s2", "s3"]].mean(axis=1, skipna=False) - df[["b1", "b2", "b3"]].mean(axis=1, skipna=False)
    return pd.DataFrame({"date": df["date"], name: v})


a = smb("6_Portfolios_2x3.csv", "bm")
b = smb("6_Portfolios_ME_OP_2x3.csv", "op")
c = smb("6_Portfolios_ME_INV_2x3.csv", "inv")
m = a.merge(b, on="date", how="inner").merge(c, on="date", how="inner")
m = m.dropna()
m["value"] = (m["bm"] + m["op"] + m["inv"]) / 3.0
m = m.sort_values("date")
m[["date", "value"]].to_csv("output.csv", index=False)
