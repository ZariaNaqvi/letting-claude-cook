import re
import numpy as np
import pandas as pd

IN_FILE = "6_Portfolios_ME_Prior_60_13.csv"
OUT_FILE = "output.csv"


def read_vw_monthly_block(path):
    """Parse the first table ('Average Value Weighted Returns -- Monthly')."""
    rows = []
    started = False
    with open(path, encoding="latin-1") as fh:
        for line in fh:
            parts = [p.strip() for p in line.strip().split(",")]
            if len(parts) >= 7 and re.fullmatch(r"\d{6}", parts[0]):
                try:
                    vals = [float(x) for x in parts[1:7]]
                except ValueError:
                    if started:
                        break
                    continue
                rows.append([int(parts[0])] + vals)
                started = True
            elif started:
                # first contiguous monthly block has ended
                break
    cols = ["date", "SL", "SM", "SH", "BL", "BM", "BH"]
    df = pd.DataFrame(rows, columns=cols)
    for c in cols[1:]:
        df[c] = df[c].replace([-99.99, -999.0, -999], np.nan)
    return df


def main():
    df = read_vw_monthly_block(IN_FILE)

    # LT_Rev: average of the two low (loser) prior-return portfolios
    # minus average of the two high (winner) prior-return portfolios
    low = df[["SL", "BL"]].mean(axis=1, skipna=False)
    high = df[["SH", "BH"]].mean(axis=1, skipna=False)
    df["value"] = low - high

    out = df.loc[df["value"].notna(), ["date", "value"]].copy()
    out["date"] = out["date"].astype(int)
    out.to_csv(OUT_FILE, index=False)


if __name__ == "__main__":
    main()
