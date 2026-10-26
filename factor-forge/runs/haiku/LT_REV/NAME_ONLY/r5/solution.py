import csv
import math

INPUT = "6_Portfolios_ME_Prior_60_13.csv"
OUTPUT = "output.csv"


def is_missing(v):
    return (abs(v + 99.99) < 1e-9) or (abs(v + 999.0) < 1e-9)


def parse_first_monthly_block(path):
    rows = []
    started = False
    with open(path, "r", encoding="latin-1") as f:
        for line in f:
            s = line.strip()
            if not s:
                if started:
                    break
                continue
            parts = [p.strip() for p in s.split(",")]
            if len(parts) >= 7 and len(parts[0]) == 6 and parts[0].isdigit():
                started = True
                try:
                    vals = []
                    for x in parts[1:7]:
                        v = float(x)
                        vals.append(math.nan if is_missing(v) else v)
                except ValueError:
                    if started:
                        break
                    continue
                rows.append((int(parts[0]), vals))
            elif started:
                break
    return rows


def main():
    rows = parse_first_monthly_block(INPUT)
    out = []
    for date, vals in rows:
        # columns: 0 SMALL LoPRIOR, 1 ME1 PRIOR2, 2 SMALL HiPRIOR,
        #          3 BIG LoPRIOR,   4 ME2 PRIOR2, 5 BIG HiPRIOR
        sl, sh = vals[0], vals[2]
        bl, bh = vals[3], vals[5]
        needed = [sl, sh, bl, bh]
        if any(math.isnan(x) for x in needed):
            continue
        lt_rev = (sl + bl) / 2.0 - (sh + bh) / 2.0
        out.append((date, lt_rev))

    with open(OUTPUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "value"])
        for date, val in out:
            w.writerow([date, repr(float(val))])


if __name__ == "__main__":
    main()
