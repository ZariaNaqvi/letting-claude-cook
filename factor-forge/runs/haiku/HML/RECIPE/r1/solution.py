import re
import numpy as np
import pandas as pd

FILE = "6_Portfolios_2x3.csv"
HEADER_TAG = "Average Value Weighted Returns -- Monthly"
COLS = ["SMALL LoBM", "ME1 BM2", "SMALL HiBM", "BIG LoBM", "ME2 BM2", "BIG HiBM"]


def read_first_monthly_block(path):
    with open(path, encoding="latin-1") as f:
        lines = f.read().splitlines()

    start = None
    for i, line in enumerate(lines):
        if HEADER_TAG in line:
            start = i
            break
    if start is None:
        raise ValueError("Could not find value-weighted monthly block")

    rows = []
    for line in lines[start + 1:]:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 7 and re.fullmatch(r"\d{6}", parts[0]):
            try:
                vals = [float(x) for x in parts[1:7]]
            except ValueError:
                if rows:
                    break
                continue
            rows.append([int(parts[0])] + vals)
        elif rows:
            # end of the first monthly block
            break

    df = pd.DataFrame(rows, columns=["date"] + COLS)
    for c in COLS:
        df[c] = df[c].replace([-99.99, -999.0, -999], np.nan)
    return df


def main():
    df = read_first_monthly_block(FILE)
    df = df.dropna(subset=COLS).copy()

    hml = (0.5 * (df["SMALL HiBM"] + df["BIG HiBM"])
           - 0.5 * (df["SMALL LoBM"] + df["BIG LoBM"]))

    out = pd.DataFrame({
        "date": df["date"].astype(int),
        "value": hml.astype(float),
    })
    out = out.sort_values("date").drop_duplicates("date")
    out.to_csv("output.csv", index=False)


if __name__ == "__main__":
    main()
