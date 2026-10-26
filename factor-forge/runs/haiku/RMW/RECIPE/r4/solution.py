import numpy as np
import pandas as pd

SRC = "6_Portfolios_ME_OP_2x3.csv"
OUT = "output.csv"
TITLE = "Average Value Weighted Returns -- Monthly"
MISSING = {-99.99, -999.0}


def parse_first_monthly_vw_block(path):
    with open(path, encoding="latin-1") as f:
        lines = f.read().splitlines()

    # locate the title of the FIRST value-weighted monthly block
    start = None
    for i, line in enumerate(lines):
        if TITLE.lower() in line.strip().lower():
            start = i
            break
    if start is None:
        raise ValueError("Monthly value-weighted block not found")

    # header line: first line after title starting with a comma
    hdr_idx = None
    for j in range(start + 1, len(lines)):
        if lines[j].strip().startswith(","):
            hdr_idx = j
            break
    if hdr_idx is None:
        raise ValueError("Header line not found")

    header = [h.strip() for h in lines[hdr_idx].strip().split(",")][1:]

    rows = []
    for k in range(hdr_idx + 1, len(lines)):
        raw = lines[k].strip()
        if not raw:
            break
        parts = [p.strip() for p in raw.split(",")]
        date_str = parts[0]
        if not (len(date_str) == 6 and date_str.isdigit()):
            break  # reached the end of the monthly block
        vals = []
        for p in parts[1:1 + len(header)]:
            try:
                v = float(p)
            except ValueError:
                v = np.nan
            if v in MISSING:
                v = np.nan
            vals.append(v)
        while len(vals) < len(header):
            vals.append(np.nan)
        rows.append([int(date_str)] + vals)

    df = pd.DataFrame(rows, columns=["date"] + header)
    return df


def main():
    df = parse_first_monthly_vw_block(SRC)

    need = ["SMALL HiOP", "BIG HiOP", "SMALL LoOP", "BIG LoOP"]
    for c in need:
        if c not in df.columns:
            raise KeyError(f"Missing column {c}; found {list(df.columns)}")

    sub = df[["date"] + need].dropna(subset=need).copy()
    sub["value"] = (
        0.5 * (sub["SMALL HiOP"] + sub["BIG HiOP"])
        - 0.5 * (sub["SMALL LoOP"] + sub["BIG LoOP"])
    )

    out = pd.DataFrame({
        "date": sub["date"].astype(int),
        "value": sub["value"].astype(float),
    }).sort_values("date").reset_index(drop=True)

    out.to_csv(OUT, index=False)


if __name__ == "__main__":
    main()
