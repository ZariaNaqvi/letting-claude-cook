import re
import numpy as np
import pandas as pd

IN_FILE = "6_Portfolios_2x3.csv"
OUT_FILE = "output.csv"
MISSING = {-99.99, -999.0, -999}


def parse_vw_monthly(path):
    with open(path, "r", encoding="latin-1") as fh:
        lines = fh.read().splitlines()

    # Locate the value-weighted monthly block
    start = 0
    for i, line in enumerate(lines):
        if "Value Weighted Returns -- Monthly" in line:
            start = i
            break

    # Find the header row of that block (contains the portfolio names)
    hdr = None
    for j in range(start, len(lines)):
        if "SMALL LoBM" in lines[j]:
            hdr = j
            break
    if hdr is None:
        for j in range(len(lines)):
            if "SMALL LoBM" in lines[j]:
                hdr = j
                break
    if hdr is None:
        raise RuntimeError("Could not find portfolio header row")

    rows = []
    for line in lines[hdr + 1:]:
        parts = [p.strip() for p in line.split(",")]
        is_data = (
            len(parts) >= 7
            and len(parts[0]) == 6
            and parts[0].isdigit()
        )
        if is_data:
            date = int(parts[0])
            vals = []
            for p in parts[1:7]:
                try:
                    v = float(p)
                except ValueError:
                    v = np.nan
                if v in MISSING:
                    v = np.nan
                vals.append(v)
            rows.append([date] + vals)
        elif rows:
            # End of the monthly VW block (blank line / next section / footer)
            break
        # else: skip blank or non-data lines before the first data row

    cols = ["date", "SL", "SM", "SH", "BL", "BM", "BH"]
    df = pd.DataFrame(rows, columns=cols)
    df["date"] = df["date"].astype(int)
    return df


def main():
    df = parse_vw_monthly(IN_FILE)

    small = df[["SL", "SM", "SH"]].mean(axis=1, skipna=True)
    big = df[["BL", "BM", "BH"]].mean(axis=1, skipna=True)
    smb = small - big

    out = pd.DataFrame({"date": df["date"].astype(int), "value": smb})
    out = out.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)
    out["date"] = out["date"].astype(int)
    out.to_csv(OUT_FILE, index=False, columns=["date", "value"])


if __name__ == "__main__":
    main()
