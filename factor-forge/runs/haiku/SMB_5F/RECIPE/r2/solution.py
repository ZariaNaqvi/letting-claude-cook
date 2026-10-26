import re
import numpy as np
import pandas as pd

FILES = [
    "6_Portfolios_2x3.csv",
    "6_Portfolios_ME_OP_2x3.csv",
    "6_Portfolios_ME_INV_2x3.csv",
]
COLS = ["s_lo", "s_me1", "s_hi", "b_lo", "b_me2", "b_hi"]


def parse_vw_monthly(path):
    with open(path, encoding="latin-1") as f:
        lines = f.readlines()

    start = None
    for i, line in enumerate(lines):
        if "Average Value Weighted Returns" in line and "Monthly" in line:
            start = i
            break
    if start is None:
        raise ValueError(f"VW monthly block not found in {path}")

    rows = []
    started = False
    for line in lines[start + 1:]:
        s = line.strip()
        if not s:
            if started:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        is_date = re.fullmatch(r"\d{6}", parts[0]) is not None
        if not started:
            if is_date:
                started = True
            else:
                continue  # column header line
        if is_date and len(parts) >= 7:
            vals = []
            for x in parts[1:7]:
                try:
                    vals.append(float(x))
                except ValueError:
                    vals.append(np.nan)
            rows.append([int(parts[0])] + vals)
        else:
            break  # end of the monthly block

    df = pd.DataFrame(rows, columns=["date"] + COLS)
    for c in COLS:
        df[c] = df[c].where(df[c] > -99.9, np.nan)  # -99.99 / -999 = missing
    return df


merged = None
for fn in FILES:
    d = parse_vw_monthly(fn)
    d = d.drop_duplicates("date").set_index("date")
    d["smb_x"] = (d[["s_lo", "s_me1", "s_hi"]].mean(axis=1)
                  - d[["b_lo", "b_me2", "b_hi"]].mean(axis=1))
    d = d[["smb_x"]].rename(columns={"smb_x": fn})
    merged = d if merged is None else merged.join(d, how="inner")

merged = merged.dropna()
merged["value"] = merged[FILES].mean(axis=1)

out = pd.DataFrame({
    "date": merged.index.astype(int),
    "value": merged["value"].values,
}).sort_values("date").reset_index(drop=True)

out.to_csv("output.csv", index=False)
