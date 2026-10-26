import re
import numpy as np
import pandas as pd

FILES = [
    "6_Portfolios_2x3.csv",          # size x BE/ME
    "6_Portfolios_ME_OP_2x3.csv",    # size x operating profitability
    "6_Portfolios_ME_INV_2x3.csv",   # size x investment
]


def parse_value_weighted(fn):
    """Parse the first 'Average Value Weighted Returns -- Monthly' block.
    Returns DataFrame indexed by YYYYMM int with 6 float columns
    (cols 0-2 = small portfolios, cols 3-5 = big portfolios).
    Missing values (-99.99 / -999) become NaN."""
    rows = {}
    in_section = False
    with open(fn, encoding="latin-1") as f:
        for line in f:
            s = line.strip()
            if not in_section:
                if "Value Weighted Returns -- Monthly" in s:
                    in_section = True
                continue
            parts = [p.strip() for p in s.split(",")]
            if len(parts) >= 7 and re.fullmatch(r"\d{6}", parts[0]):
                date = int(parts[0])
                vals = []
                for p in parts[1:7]:
                    try:
                        v = float(p)
                    except ValueError:
                        v = np.nan
                    if v == -99.99 or v == -999.0:
                        v = np.nan
                    vals.append(v)
                rows[date] = vals
            else:
                if rows:  # end of the monthly value-weighted block
                    break
    df = pd.DataFrame.from_dict(rows, orient="index", columns=list(range(6)))
    return df.sort_index()


def sub_factor(df):
    """Small-minus-big spread for one 2x3 sort: avg(3 small) - avg(3 big)."""
    small = df.iloc[:, 0:3].mean(axis=1, skipna=False)
    big = df.iloc[:, 3:6].mean(axis=1, skipna=False)
    return small - big


def main():
    subs = []
    for fn in FILES:
        df = parse_value_weighted(fn)
        subs.append(sub_factor(df).rename(fn))

    combined = pd.concat(subs, axis=1, join="inner").dropna()
    smb = combined.mean(axis=1)

    out = pd.DataFrame({
        "date": smb.index.astype(int),
        "value": smb.values.astype(float),
    })
    out = out.sort_values("date").reset_index(drop=True)
    out.to_csv("output.csv", index=False)


if __name__ == "__main__":
    main()
