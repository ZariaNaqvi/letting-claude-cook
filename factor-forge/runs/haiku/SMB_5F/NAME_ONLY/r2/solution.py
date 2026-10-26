import re
import numpy as np
import pandas as pd

FILES = [
    "6_Portfolios_2x3.csv",          # size x B/M
    "6_Portfolios_ME_OP_2x3.csv",    # size x OP
    "6_Portfolios_ME_INV_2x3.csv",   # size x Inv
]
MISSING = (-99.99, -999.0)


def read_vw_monthly(path):
    """Parse the 'Average Value Weighted Returns -- Monthly' block of a Ken French file.
    Returns a DataFrame indexed by YYYYMM int with 6 columns in file order:
    SMALL Lo, ME1 mid, SMALL Hi, BIG Lo, ME2 mid, BIG Hi."""
    with open(path, encoding="latin-1") as f:
        lines = f.read().splitlines()

    start = None
    for i, line in enumerate(lines):
        low = line.lower()
        if "value weighted returns" in low and "monthly" in low:
            start = i
            break
    if start is None:
        start = -1  # fallback: scan whole file

    rows = []
    started = False
    for line in lines[start + 1:]:
        parts = [p.strip() for p in line.split(",")]
        if parts and re.fullmatch(r"\d{6}", parts[0]) and len(parts) >= 7:
            vals = []
            for p in parts[1:7]:
                try:
                    v = float(p)
                except ValueError:
                    v = np.nan
                if any(np.isclose(v, m) for m in MISSING):
                    v = np.nan
                vals.append(v)
            rows.append([int(parts[0])] + vals)
            started = True
        elif started:
            break  # end of the monthly block

    df = pd.DataFrame(rows, columns=["date"] + list(range(6)))
    df = df.set_index("date").sort_index()
    return df


def size_factor_from_file(path):
    d = read_vw_monthly(path)
    small = d[[0, 1, 2]].mean(axis=1, skipna=False)  # avg of 3 small portfolios
    big = d[[3, 4, 5]].mean(axis=1, skipna=False)    # avg of 3 big portfolios
    return small - big


def main():
    series = [size_factor_from_file(f) for f in FILES]
    # Align on months where all three sorts are available
    combined = pd.concat(series, axis=1, join="inner").dropna()
    smb = combined.mean(axis=1)  # SMB = (SMB_BM + SMB_OP + SMB_INV) / 3

    out = pd.DataFrame({
        "date": smb.index.astype(int),
        "value": smb.values.astype(float),
    })
    out = out.sort_values("date").reset_index(drop=True)
    out.to_csv("output.csv", index=False)


if __name__ == "__main__":
    main()
