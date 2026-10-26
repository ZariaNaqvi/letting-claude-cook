import csv
import pandas as pd

files = ["6_Portfolios_2x3.csv", "6_Portfolios_ME_OP_2x3.csv", "6_Portfolios_ME_INV_2x3.csv"]


def read_block(fn):
    with open(fn, "r", encoding="latin-1") as f:
        lines = f.read().splitlines()
    start = None
    for i, l in enumerate(lines):
        if "Average Value Weighted Returns" in l and "Monthly" in l:
            start = i
            break
    rows = {}
    for l in lines[start + 1:]:
        parts = [p.strip() for p in l.split(",")]
        if len(parts) >= 7 and parts[0].isdigit() and len(parts[0]) == 6:
            try:
                vals = [float(x) for x in parts[1:7]]
            except ValueError:
                continue
            rows[int(parts[0])] = vals
        elif len(parts) >= 7 and parts[0] == "":
            continue  # header
        else:
            if rows:
                break
    df = pd.DataFrame.from_dict(rows, orient="index")
    df = df.mask((df <= -99.0))
    return df


series = []
for fn in files:
    df = read_block(fn)
    small = df[[0, 1, 2]].mean(axis=1, skipna=False)
    big = df[[3, 4, 5]].mean(axis=1, skipna=False)
    series.append(small - big)

comb = pd.concat(series, axis=1, join="inner").dropna()
val = comb.mean(axis=1)
out = pd.DataFrame({"date": comb.index.astype(int), "value": val.values})
out = out.sort_values("date")
out.to_csv("output.csv", index=False)
