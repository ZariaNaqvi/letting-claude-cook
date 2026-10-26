import pandas as pd
import numpy as np

files = ["6_Portfolios_2x3.csv", "6_Portfolios_ME_OP_2x3.csv", "6_Portfolios_ME_INV_2x3.csv"]

def read_first_block(fn):
    with open(fn, encoding="latin-1") as f:
        lines = f.read().splitlines()
    start = None
    for i, l in enumerate(lines):
        if "Value Weighted Returns" in l and "Monthly" in l:
            start = i
            break
    rows = []
    seen = False
    for l in lines[start + 1:]:
        parts = [p.strip() for p in l.split(",")]
        if parts and len(parts[0]) == 6 and parts[0].isdigit() and len(parts) >= 7:
            try:
                vals = [float(x) for x in parts[1:7]]
            except ValueError:
                break
            rows.append([int(parts[0])] + vals)
            seen = True
        else:
            if seen:
                break
    df = pd.DataFrame(rows, columns=["date", "a", "b", "c", "d", "e", "f"]).set_index("date")
    df = df.mask((df <= -99.99))
    return df

series = []
for fn in files:
    df = read_first_block(fn)
    s = df[["a", "b", "c"]].mean(axis=1, skipna=False) - df[["d", "e", "f"]].mean(axis=1, skipna=False)
    series.append(s.rename(fn))

m = pd.concat(series, axis=1, join="inner").dropna()
out = pd.DataFrame({"date": m.index.astype(int), "value": m.mean(axis=1).values})
out.to_csv("output.csv", index=False)
