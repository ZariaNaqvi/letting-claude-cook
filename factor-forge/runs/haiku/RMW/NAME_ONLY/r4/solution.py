import csv
import math

IN_FILE = "6_Portfolios_ME_OP_2x3.csv"
OUT_FILE = "output.csv"
MISSING = {-99.99, -999.0}


def is_yyyymm(tok):
    tok = tok.strip()
    return len(tok) == 6 and tok.isdigit()


def parse_value(tok):
    try:
        v = float(tok.strip())
    except ValueError:
        return float("nan")
    if v in MISSING or v <= -99.98 and v >= -100.0 and abs(v + 99.99) < 1e-9:
        return float("nan")
    return v


def main():
    with open(IN_FILE, "r", encoding="latin-1", errors="replace") as f:
        lines = f.read().splitlines()

    # Locate the value-weighted monthly block
    start = None
    for i, line in enumerate(lines):
        if "Value Weighted" in line and "Monthly" in line:
            start = i + 1
            break
    if start is None:
        start = 0  # fallback: scan whole file for first YYYYMM block

    rows = []
    started = False
    for line in lines[start:]:
        s = line.strip()
        if not s:
            if started:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if is_yyyymm(parts[0]) and len(parts) >= 7:
            started = True
            date = int(parts[0])
            vals = [parse_value(p) for p in parts[1:7]]
            rows.append((date, vals))
        else:
            if started:
                break  # end of monthly block (e.g., annual section or footer)

    out = []
    for date, v in rows:
        small_lo, small_mid, small_hi, big_lo, big_mid, big_hi = v
        r = 0.5 * (small_hi + big_hi) - 0.5 * (small_lo + big_lo)
        if math.isnan(r):
            continue
        out.append((date, r))

    with open(OUT_FILE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "value"])
        for date, r in out:
            w.writerow([date, repr(float(r))])


if __name__ == "__main__":
    main()
