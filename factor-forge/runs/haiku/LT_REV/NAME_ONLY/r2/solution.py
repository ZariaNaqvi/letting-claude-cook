import csv

INPUT = "6_Portfolios_ME_Prior_60_13.csv"
OUTPUT = "output.csv"
MISSING = {-99.99, -999.0}


def main():
    with open(INPUT, encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the start of the value-weighted monthly table
    start = 0
    for i, line in enumerate(lines):
        if "Average Value Weighted Returns" in line and "Monthly" in line:
            start = i
            break

    records = []
    started = False
    for line in lines[start + 1:]:
        parts = [p.strip() for p in line.split(",")]
        is_data = (
            len(parts) >= 7
            and len(parts[0]) == 6
            and parts[0].isdigit()
        )
        if not is_data:
            if started:
                break  # end of the monthly value-weighted block
            continue
        try:
            date = int(parts[0])
            vals = []
            for x in parts[1:7]:
                v = float(x)
                vals.append(None if v in MISSING else v)
        except ValueError:
            if started:
                break
            continue
        started = True
        records.append((date, vals))

    out_rows = []
    for date, v in records:
        # Column order: SMALL LoPRIOR, ME1 PRIOR2, SMALL HiPRIOR,
        #               BIG LoPRIOR, ME2 PRIOR2, BIG HiPRIOR
        sm_lo, sm_hi, big_lo, big_hi = v[0], v[2], v[3], v[5]
        if None in (sm_lo, sm_hi, big_lo, big_hi):
            continue
        # LT reversal: long Low prior-return (losers), short High prior-return (winners)
        value = 0.5 * (sm_lo + big_lo) - 0.5 * (sm_hi + big_hi)
        out_rows.append((date, value))

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "value"])
        for date, value in out_rows:
            writer.writerow([date, repr(float(value))])


if __name__ == "__main__":
    main()
