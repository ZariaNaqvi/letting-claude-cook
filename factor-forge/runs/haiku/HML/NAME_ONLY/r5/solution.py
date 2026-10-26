import re
import math
import pandas as pd


def _num(s):
    try:
        v = float(s.strip())
    except (ValueError, AttributeError):
        return math.nan
    if v in (-99.99, -999.0):
        return math.nan
    return v


def main():
    with open("6_Portfolios_2x3.csv", encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the value-weighted monthly section
    vw_title = None
    for i, l in enumerate(lines):
        if "Value Weighted" in l and "Monthly" in l:
            vw_title = i
            break
    if vw_title is None:
        vw_title = 0

    # Locate header line of that section
    hdr = None
    for j in range(vw_title + 1, len(lines)):
        if "LoBM" in lines[j] and "HiBM" in lines[j]:
            hdr = j
            break
    if hdr is None:
        raise RuntimeError("Could not find portfolio header line")

    cols = [c.strip() for c in lines[hdr].split(",")]

    def find_col(pred):
        for idx, c in enumerate(cols):
            if pred(c):
                return idx
        raise RuntimeError("Required column not found")

    i_sl = find_col(lambda c: "SMALL" in c and "LoBM" in c)
    i_sh = find_col(lambda c: "SMALL" in c and "HiBM" in c)
    i_bl = find_col(lambda c: "BIG" in c and "LoBM" in c)
    i_bh = find_col(lambda c: "BIG" in c and "HiBM" in c)

    records = []
    started = False
    for l in lines[hdr + 1:]:
        parts = [p.strip() for p in l.split(",")]
        if parts and re.fullmatch(r"\d{6}", parts[0] or ""):
            started = True
            date = int(parts[0])
            if len(parts) <= max(i_sl, i_sh, i_bl, i_bh):
                continue
            sl = _num(parts[i_sl])
            sh = _num(parts[i_sh])
            bl = _num(parts[i_bl])
            bh = _num(parts[i_bh])
            hml = 0.5 * (sh + bh) - 0.5 * (sl + bl)
            records.append((date, hml))
        else:
            if started:
                # End of the monthly block (blank line or next section/footer)
                break

    df = pd.DataFrame(records, columns=["date", "value"])
    df = df.dropna(subset=["value"])
    df["date"] = df["date"].astype(int)
    df = df.drop_duplicates(subset=["date"], keep="first").sort_values("date")
    df.to_csv("output.csv", index=False)


if __name__ == "__main__":
    main()
