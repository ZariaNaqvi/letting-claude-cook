import re

INPUT_FILE = "6_Portfolios_ME_Prior_60_13.csv"
OUTPUT_FILE = "output.csv"
MISSING = {-99.99, -999.0}


def parse_monthly_section(path):
    with open(path, encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the monthly value-weighted returns section
    start = None
    for i, line in enumerate(lines):
        if "Average Value Weighted Returns" in line and "Monthly" in line:
            start = i
            break
    if start is None:
        raise RuntimeError("Monthly value-weighted section not found")

    rows = []
    started = False
    date_re = re.compile(r"^\d{6}$")
    for line in lines[start + 1:]:
        s = line.strip()
        if not s:
            if started:
                break  # end of monthly block
            continue
        parts = [p.strip() for p in s.split(",")]
        if date_re.match(parts[0]) and len(parts) >= 7:
            started = True
            vals = []
            for p in parts[1:7]:
                try:
                    v = float(p)
                except ValueError:
                    v = float("nan")
                if v in MISSING:
                    v = float("nan")
                vals.append(v)
            rows.append((int(parts[0]), vals))
        else:
            if started:
                break  # reached next section
    return rows


def main():
    rows = parse_monthly_section(INPUT_FILE)

    # Column order in file:
    # 0 SMALL LoPRIOR, 1 ME1 PRIOR2, 2 SMALL HiPRIOR,
    # 3 BIG LoPRIOR,   4 ME2 PRIOR2, 5 BIG HiPRIOR
    out = []
    for date, v in rows:
        small_lo, small_hi = v[0], v[2]
        big_lo, big_hi = v[3], v[5]
        ret = 0.5 * (small_lo + big_lo) - 0.5 * (small_hi + big_hi)
        if ret != ret:  # NaN check
            continue
        out.append((date, ret))

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        f.write("date,value\n")
        for date, ret in out:
            f.write(f"{date},{ret:.6f}\n")


if __name__ == "__main__":
    main()
