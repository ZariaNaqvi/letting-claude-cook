import pandas as pd
import numpy as np

SRC = "6_Portfolios_ME_Prior_12_2.csv"
OUT = "output.csv"


def is_missing(v):
    return v is None or (not np.isfinite(v)) or v <= -99.0


def parse_first_monthly_block(path):
    header = None
    data = []
    started = False
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                if started:
                    break
                continue
            parts = [p.strip() for p in raw.split(",")]
            is_data = (
                len(parts) >= 2
                and parts[0].isdigit()
                and len(parts[0]) == 6
            )
            if is_data:
                try:
                    vals = []
                    for x in parts[1:]:
                        if x == "":
                            vals.append(np.nan)
                        else:
                            vals.append(float(x))
                except ValueError:
                    if started:
                        break
                    continue
                data.append((int(parts[0]), vals))
                started = True
            else:
                if started:
                    # end of the first monthly value-weighted block
                    break
                if "SMALL LoPRIOR" in raw or "SMALL HiPRIOR" in raw:
                    header = parts
    return header, data


def main():
    header, data = parse_first_monthly_block(SRC)

    # Locate the four corner portfolios by name (fallback to standard positions)
    idx = {"SL": 0, "SH": 2, "BL": 3, "BH": 5}
    if header is not None:
        names = [h.strip() for h in header]
        # header[0] is blank (date column); portfolio names start at index 1
        def find(name):
            for i, h in enumerate(names):
                if h.upper() == name.upper():
                    return i - 1  # shift because data index 0 is first portfolio
            return None
        s_lo = find("SMALL LoPRIOR")
        s_hi = find("SMALL HiPRIOR")
        b_lo = find("BIG LoPRIOR")
        b_hi = find("BIG HiPRIOR")
        if None not in (s_lo, s_hi, b_lo, b_hi):
            idx = {"SL": s_lo, "SH": s_hi, "BL": b_lo, "BH": b_hi}

    recs = []
    for date, vals in data:
        def g(key):
            j = idx[key]
            if j >= len(vals):
                return np.nan
            v = vals[j]
            return np.nan if is_missing(v) else v

        sl, sh, bl, bh = g("SL"), g("SH"), g("BL"), g("BH")
        if np.isnan([sl, sh, bl, bh]).any():
            continue
        umd = 0.5 * (sh + bh) - 0.5 * (sl + bl)
        recs.append((date, umd))

    df = pd.DataFrame(recs, columns=["date", "value"])
    df["date"] = df["date"].astype(int)
    df = df.drop_duplicates(subset="date", keep="first").sort_values("date")
    df.to_csv(OUT, index=False, columns=["date", "value"])


if __name__ == "__main__":
    main()
