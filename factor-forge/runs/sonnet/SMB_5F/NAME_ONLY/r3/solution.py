import re
import numpy as np
import pandas as pd


def read_first_section(fname):
    rows = {}
    started = False
    with open(fname, "r", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not started:
                if "Value Weighted Returns" in s and "Monthly" in s:
                    started = True
                    seen_data = False
                continue
            parts = [p.strip() for p in s.split(",")]
            if len(parts) >= 7 and re.fullmatch(r"\d{6}", parts[0]):
                seen_data = True
                vals = []
                for p in parts[1:7]:
                    try:
                        v = float(p)
                    except ValueError:
                        v = np.nan
                    if v <= -99.0:
                        v = np.nan
                    vals.append(v)
                rows[int(parts[0])] = vals
            else:
                if seen_data:
                    break
    df = pd.DataFrame.from_dict(rows, orient="index")
    return df


def smb_part(df):
    return df.iloc[:, 0:3].mean(axis=1, skipna=False) - df.iloc[:, 3:6].mean(axis=1, skipna=False)


bm = smb_part(read_first_section("6_Portfolios_2x3.csv"))
op = smb_part(read_first_section("6_Portfolios_ME_OP_2x3.csv"))
inv = smb_part(read_first_section("6_Portfolios_ME_INV_2x3.csv"))

d = pd.concat([bm, op, inv], axis=1, join="inner")
d.columns = ["bm", "op", "inv"]
d = d.dropna()
out = pd.DataFrame({"date": d.index.astype(int), "value": d.mean(axis=1).values})
out = out.sort_values("date")
out.to_csv("output.csv", index=False)
