import re
import numpy as np
import pandas as pd

SRC = "6_Portfolios_ME_Prior_1_0.csv"
OUT = "output.csv"


def is_missing(v):
    return (abs(v + 99.99) < 1e-6) or (abs(v + 999.0) < 1e-6)


def main():
    with open(SRC, encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the first monthly value-weighted table
    start = None
    for i, l in enumerate(lines):
        if "value weighted returns" in l.lower() and "monthly" in l.lower():
            start = i
            break
    if start is None:
        raise RuntimeError("Monthly value-weighted table not found")

    records = []
    started = False
    for l in lines[start + 1:]:
        parts = [p.strip() for p in l.split(",")]
        if parts and re.fullmatch(r"\d{6}", parts[0]) and len(parts) >= 7:
            vals = []
            ok = True
            for p in parts[1:7]:
                try:
                    v = float(p)
                except ValueError:
                    ok = False
                    break
                vals.append(np.nan if is_missing(v) else v)
            if not ok:
                if started:
                    break
                continue
            records.append([int(parts[0])] + vals)
            started = True
        elif started:
            # end of the monthly block
            break

    df = pd.DataFrame(
        records,
        columns=["date", "SL", "ML", "SH", "BL", "MB", "BH"],
    )

    # Column order in file: SMALL LoPRIOR, ME1 PRIOR2, SMALL HiPRIOR,
    #                       BIG LoPRIOR, ME2 PRIOR2, BIG HiPRIOR
    # ST_Rev = 0.5*(Small Lo + Big Lo) - 0.5*(Small Hi + Big Hi)
    df = df.dropna(subset=["SL", "SH", "BL", "BH"]).copy()
    df["value"] = 0.5 * (df["SL"] + df["BL"]) - 0.5 * (df["SH"] + df["BH"])

    out = pd.DataFrame({
        "date": df["date"].astype(int),
        "value": df["value"].astype(float),
    })
    out.to_csv(OUT, index=False)


if __name__ == "__main__":
    main()
