import re
import pandas as pd
import numpy as np

SRC = "6_Portfolios_ME_INV_2x3.csv"
OUT = "output.csv"


def norm(s):
    return re.sub(r"\s+", " ", s.strip()).upper()


def main():
    with open(SRC, encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the header of the first (value-weighted monthly) table.
    hdr = None
    for i, l in enumerate(lines):
        if l.startswith(",") and "SMALL" in l.upper() and "LOINV" in l.upper():
            hdr = i
            break
    if hdr is None:
        raise RuntimeError("Could not find header line in input file")

    cols = [norm(c) for c in lines[hdr].split(",")][1:]

    def idx(name):
        target = norm(name)
        for k, c in enumerate(cols):
            if c == target:
                return k
        raise RuntimeError(f"Column {name} not found in header: {cols}")

    i_sl = idx("SMALL LoINV")
    i_sh = idx("SMALL HiINV")
    i_bl = idx("BIG LoINV")
    i_bh = idx("BIG HiINV")
    ncols = len(cols)

    records = []
    started = False
    for l in lines[hdr + 1:]:
        s = l.strip()
        if not s:
            if started:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if re.fullmatch(r"\d{6}", parts[0]):
            started = True
            vals = []
            for k in range(ncols):
                if k + 1 < len(parts):
                    try:
                        v = float(parts[k + 1])
                    except ValueError:
                        v = np.nan
                else:
                    v = np.nan
                if v in (-99.99, -999.0):
                    v = np.nan
                vals.append(v)
            records.append((int(parts[0]), vals))
        else:
            if started:
                break

    rows = []
    for date, vals in records:
        sl, sh, bl, bh = vals[i_sl], vals[i_sh], vals[i_bl], vals[i_bh]
        cma = 0.5 * (sl + bl) - 0.5 * (sh + bh)
        if np.isnan(cma):
            continue
        rows.append((date, cma))

    out = pd.DataFrame(rows, columns=["date", "value"])
    out["date"] = out["date"].astype(int)
    out.to_csv(OUT, index=False)


if __name__ == "__main__":
    main()
