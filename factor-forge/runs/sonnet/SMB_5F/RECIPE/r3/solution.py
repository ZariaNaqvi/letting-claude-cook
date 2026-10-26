import pandas as pd
import numpy as np

def read_first_block(fn):
    rows = []
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
            if parts[0].isdigit() and len(parts[0]) == 6:
                rows.append(parts)
            elif rows:
                break
            else:
                continue  # header line
    df = pd.DataFrame(rows)
    df = df.iloc[:, :7]
    df.columns = ["date", "c1", "c2", "c3", "c4", "c5", "c6"]
    df["date"] = df["date"].astype(int)
    for c in df.columns[1:]:
        v = pd.to_numeric(df[c], errors="coerce")
        v = v.where(~v.isin([-99.99, -999, -999.0]))
        df[c] = v
    df = df.set_index("date")
    small = df[["c1", "c2", "c3"]].mean(axis=1, skipna=False)
    big = df[["c4", "c5", "c6"]].mean(axis=1, skipna=False)
    return small - big

files = ["6_Portfolios_2x3.csv", "6_Portfolios_ME_OP_2x3.csv", "6_Portfolios_ME_INV_2x3.csv"]
series = [read_first_block(f) for f in files]
d = pd.concat(series, axis=1, join="inner")
d.columns = ["a", "b", "c"]
d = d.dropna()
out = pd.DataFrame({"date": d.index.astype(int), "value": d.mean(axis=1).values})
out = out.sort_values("date")
out.to_csv("output.csv", index=False)
