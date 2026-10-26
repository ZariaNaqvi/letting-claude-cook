import re
import numpy as np
import pandas as pd

SRC = "6_Portfolios_ME_Prior_12_2.csv"
OUT = "output.csv"
MISSING = {-99.99, -999.0}


def main():
    with open(SRC, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    # Locate the first monthly value-weighted block
    start = None
    for i, line in enumerate(lines):
        low = line.lower()
        if "value weighted" in low and "monthly" in low:
            start = i
            break
    if start is None:
        raise RuntimeError("Monthly value-weighted block not found")

    # Find the column header line (begins with a comma, contains portfolio names)
    hdr_idx = None
    for j in range(start + 1, len(lines)):
        if lines[j].strip() and "," in lines[j]:
            hdr_idx = j
            break
    if hdr_idx is None:
        raise RuntimeError("Header line not found")

    header = [h.strip() for h in lines[hdr_idx].split(",")]
    # header[0] is the blank index column
    def find_col(name):
        for k, h in enumerate(header):
            if h.upper() == name.upper():
                return k
        return None

    c_sl = find_col("SMALL LoPRIOR")
    c_sh = find_col("SMALL HiPRIOR")
    c_bl = find_col("BIG LoPRIOR")
    c_bh = find_col("BIG HiPRIOR")
    if None in (c_sl, c_sh, c_bl, c_bh):
        # Fallback to known positions
        c_sl, c_sh, c_bl, c_bh = 1, 3, 4, 6

    # Read data rows
    records = []
    started = False
    for j in range(hdr_idx + 1, len(lines)):
        raw = lines[j].strip()
        if not raw:
            if started:
                break
            continue
        parts = [p.strip() for p in raw.split(",")]
        tok = parts[0]
        if re.fullmatch(r"\d{6}", tok):
            started = True
            vals = []
            for p in parts[1:]:
                try:
                    v = float(p)
                except ValueError:
                    v = np.nan
                if v in MISSING:
                    v = np.nan
                vals.append(v)
            records.append((int(tok), vals))
        else:
            if started:
                break

    rows = []
    for date, vals in records:
        def g(c):
            idx = c - 1  # vals excludes the date column
            if idx < 0 or idx >= len(vals):
                return np.nan
            return vals[idx]
        sl, sh, bl, bh = g(c_sl), g(c_sh), g(c_bl), g(c_bh)
        mom = 0.5 * (sh + bh) - 0.5 * (sl + bl)
        rows.append((date, mom))

    out = pd.DataFrame(rows, columns=["date", "value"])
    out = out.dropna(subset=["value"])
    out["date"] = out["date"].astype(int)
    out.to_csv(OUT, index=False)


if __name__ == "__main__":
    main()
