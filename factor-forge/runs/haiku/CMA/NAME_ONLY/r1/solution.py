import numpy as np
import pandas as pd

INPUT = "6_Portfolios_ME_INV_2x3.csv"
OUTPUT = "output.csv"


def norm(s):
    return "".join(s.split()).lower()


def is_date(tok):
    return len(tok) == 6 and tok.isdigit()


def main():
    with open(INPUT, encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the first block: Average Value Weighted Returns -- Monthly
    start = None
    for i, ln in enumerate(lines):
        low = ln.lower()
        if "value weighted" in low and "monthly" in low:
            start = i
            break
    if start is None:
        raise SystemExit("Could not find value-weighted monthly block")

    # Header line: begins with a comma and contains portfolio names
    hdr_idx = None
    for j in range(start + 1, len(lines)):
        if lines[j].strip().startswith(","):
            hdr_idx = j
            break
    if hdr_idx is None:
        raise SystemExit("Header not found")

    header = [h.strip() for h in lines[hdr_idx].split(",")]
    names = [norm(h) for h in header]

    def find_col(target, fallback):
        if target in names:
            return names.index(target)
        return fallback

    # Expected order: date, SMALL LoINV, ME1 INV2, SMALL HiINV, BIG LoINV, ME2 INV2, BIG HiINV
    c_sl = find_col("smallloinv", 1)
    c_sh = find_col("smallhiinv", 3)
    c_bl = find_col("bigloinv", 4)
    c_bh = find_col("bighiinv", 6)

    rows = []
    started = False
    for j in range(hdr_idx + 1, len(lines)):
        ln = lines[j]
        parts = [p.strip() for p in ln.split(",")]
        if parts and is_date(parts[0]):
            started = True
            rows.append(parts)
        else:
            if started:
                break  # end of monthly block
            # skip blank/other lines before data starts

    def num(s):
        try:
            v = float(s)
        except ValueError:
            return np.nan
        if v <= -99.0:  # -99.99 or -999 missing markers
            return np.nan
        return v

    recs = []
    for parts in rows:
        vals = {}
        for key, c in (("sl", c_sl), ("sh", c_sh), ("bl", c_bl), ("bh", c_bh)):
            vals[key] = num(parts[c]) if c < len(parts) else np.nan
        recs.append((int(parts[0]), vals["sl"], vals["sh"], vals["bl"], vals["bh"]))

    df = pd.DataFrame(recs, columns=["date", "sl", "sh", "bl", "bh"])
    df = df.dropna(subset=["sl", "sh", "bl", "bh"])

    # CMA = avg(Small LoINV, Big LoINV) - avg(Small HiINV, Big HiINV)
    df["value"] = 0.5 * (df["sl"] + df["bl"]) - 0.5 * (df["sh"] + df["bh"])

    out = df[["date", "value"]].copy()
    out["date"] = out["date"].astype(int)
    out.to_csv(OUTPUT, index=False)


if __name__ == "__main__":
    main()
