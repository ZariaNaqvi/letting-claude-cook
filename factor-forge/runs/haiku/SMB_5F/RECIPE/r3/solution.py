import re
import numpy as np
import pandas as pd

FILES = [
    "6_Portfolios_2x3.csv",
    "6_Portfolios_ME_OP_2x3.csv",
    "6_Portfolios_ME_INV_2x3.csv",
]
TITLE = "Average Value Weighted Returns -- Monthly"
MISSING = {-99.99, -999.0, -999}


def parse_first_vw_monthly(path):
    """Parse the first 'Average Value Weighted Returns -- Monthly' block.
    Returns (dataframe indexed by YYYYMM int, list of column names)."""
    with open(path, encoding="latin-1") as f:
        lines = f.read().splitlines()

    start = None
    for i, line in enumerate(lines):
        if TITLE in line:
            start = i
            break
    if start is None:
        raise ValueError(f"Block not found in {path}")

    header = None
    rows = []
    for line in lines[start + 1:]:
        s = line.strip()
        if not s:
            if rows:          # blank line after data ends the block
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if header is None:
            header = parts    # first non-empty line after title is the header
            continue
        if re.fullmatch(r"\d{6}", parts[0]):
            rows.append(parts)
        elif rows:            # next block/annual section begins
            break

    if header is None or not rows:
        raise ValueError(f"No data parsed from {path}")

    names = header[1:]
    ncol = len(names)
    data = []
    dates = []
    for parts in rows:
        dates.append(int(parts[0]))
        vals = []
        for j in range(1, ncol + 1):
            try:
                v = float(parts[j]) if j < len(parts) and parts[j] != "" else np.nan
            except ValueError:
                v = np.nan
            if v in MISSING:
                v = np.nan
            vals.append(v)
        data.append(vals)

    df = pd.DataFrame(data, index=pd.Index(dates, name="date"), columns=names)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df, names


def smb_from_file(path):
    df, names = parse_first_vw_monthly(path)
    small_cols = [c for c in names if "SMALL" in c.upper()]
    big_cols = [c for c in names if "BIG" in c.upper()]
    if len(small_cols) != 3 or len(big_cols) != 3:
        # fallback: first three are small, last three are big
        small_cols = names[:3]
        big_cols = names[3:6]
    smb = df[small_cols].mean(axis=1) - df[big_cols].mean(axis=1)
    return smb


def main():
    series = [smb_from_file(f) for f in FILES]

    common = series[0].index
    for s in series[1:]:
        common = common.intersection(s.index)
    common = common[common >= 196307]
    common = sorted(common)

    mat = pd.concat([s.reindex(common) for s in series], axis=1)
    mat.columns = range(len(series))
    smb = mat.mean(axis=1)          # equal 1/3 weighting of the three SMB's
    smb = smb.dropna()

    out = pd.DataFrame({
        "date": [int(d) for d in smb.index],
        "value": smb.values.astype(float),
    })
    out.to_csv("output.csv", index=False)


if __name__ == "__main__":
    main()
