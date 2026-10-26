import re
import csv

INFILE = "6_Portfolios_2x3.csv"
OUTFILE = "output.csv"

MISSING_VALUES = (-99.99, -999.0)


def is_missing(v):
    return any(abs(v - m) < 1e-9 for m in MISSING_VALUES)


def parse_value_weighted_monthly(path):
    """
    Parse the first monthly block (Average Value Weighted Returns -- Monthly).
    Returns list of (yyyymm:int, [six floats or None]).
    """
    date_re = re.compile(r"^\s*(\d{6})\s*,(.*)$")
    rows = []
    started = False
    with open(path, "r", encoding="latin-1") as f:
        for line in f:
            s = line.strip()
            m = date_re.match(s)
            if m:
                started = True
                parts = [p.strip() for p in m.group(2).split(",")]
                if len(parts) < 6:
                    continue
                vals = []
                for p in parts[:6]:
                    try:
                        v = float(p)
                    except ValueError:
                        vals.append(None)
                        continue
                    if is_missing(v):
                        vals.append(None)
                    else:
                        vals.append(v)
                rows.append((int(m.group(1)), vals))
            else:
                # End of the contiguous monthly value-weighted block
                if started:
                    break
    return rows


def main():
    rows = parse_value_weighted_monthly(INFILE)

    out = []
    seen = set()
    for date, vals in rows:
        if date in seen:
            continue
        seen.add(date)
        if any(v is None for v in vals):
            continue
        # Columns: SMALL LoBM, ME1 BM2, SMALL HiBM, BIG LoBM, ME2 BM2, BIG HiBM
        small = (vals[0] + vals[1] + vals[2]) / 3.0
        big = (vals[3] + vals[4] + vals[5]) / 3.0
        out.append((date, small - big))

    out.sort(key=lambda x: x[0])

    with open(OUTFILE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "value"])
        for date, val in out:
            w.writerow([date, repr(float(val))])


if __name__ == "__main__":
    main()
