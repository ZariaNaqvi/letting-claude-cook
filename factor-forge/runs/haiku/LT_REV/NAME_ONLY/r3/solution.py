import re
import numpy as np
import pandas as pd


def parse_value(tok):
    tok = tok.strip()
    try:
        v = float(tok)
    except ValueError:
        return np.nan
    if abs(v + 99.99) < 1e-6 or abs(v + 999.0) < 1e-6:
        return np.nan
    return v


def main():
    fname = "6_Portfolios_ME_Prior_60_13.csv"
    with open(fname, encoding="latin-1") as f:
        lines = f.readlines()

    rows = []
    started = False
    for line in lines:
        parts = [p.strip() for p in line.strip().split(",")]
        if len(parts) == 7 and re.fullmatch(r"\d{6}", parts[0]):
            rows.append([int(parts[0])] + [parse_value(p) for p in parts[1:]])
            started = True
        elif started:
            # first monthly value-weighted block has ended
            break

    cols = ["date", "SL", "SM", "SH", "BL", "BM", "BH"]
    df = pd.DataFrame(rows, columns=cols)

    # Long-term reversal: losers (LoPRIOR) minus winners (HiPRIOR), averaged over size
    lt = 0.5 * (df["SL"] + df["BL"]) - 0.5 * (df["SH"] + df["BH"])

    out = pd.DataFrame({"date": df["date"].astype(int), "value": lt})
    out = out.dropna().reset_index(drop=True)
    out["date"] = out["date"].astype(int)

    out.to_csv("output.csv", index=False, columns=["date", "value"])


if __name__ == "__main__":
    main()
