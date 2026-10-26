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
            if not s:
                if rows:
                    break
                continue
            parts = [p.strip() for p in s.split(",")]
            if parts[0] == "":
                # header line
                if rows:
                    break
                continue
            if not (parts[0].isdigit() and len(parts[0]) == 6):
                if rows:
                    break
                continue
            if len(parts) < 7:
                break
            try:
                vals = [float(x) for x in parts[1:7]]
            except ValueError:
                break
            vals = [np.nan if (v <= -99.99) else v for v in vals]
            rows[int(parts[0])] = vals
    df = pd.DataFrame.from_dict(rows, orient="index")
    return df

def smb(fn):
    df = read_first_block(fn)
    return df.iloc[:, 0:3].mean(axis=1, skipna=False) - df.iloc[:, 3:6].mean(axis=1, skipna=False)

a = smb("6_Portfolios_2x3.csv")
b = smb("6_Portfolios_ME_OP_2x3.csv")
c = smb("6_Portfolios_ME_INV_2x3.csv")

d = pd.concat([a, b, c], axis=1, join="inner").dropna()
val = d.mean(axis=1)
out = pd.DataFrame({"date": val.index.astype(int), "value": val.values})
out = out.sort_values("date")
out.to_csv("output.csv", index=False)
