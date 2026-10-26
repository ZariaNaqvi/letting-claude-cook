import re
import math

INPUT = "6_Portfolios_ME_OP_2x3.csv"
OUTPUT = "output.csv"

DATA_RE = re.compile(r"^\s*(\d{6})\s*,")


def is_missing(x):
    return x is None or math.isnan(x) or abs(x + 99.99) < 1e-6 or abs(x + 999.0) < 1e-6


def to_float(s):
    s = s.strip()
    if s == "":
        return float("nan")
    try:
        v = float(s)
    except ValueError:
        return float("nan")
    if is_missing(v):
        return float("nan")
    return v


def main():
    with open(INPUT, "r", encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the value-weighted monthly section
    start = None
    for i, line in enumerate(lines):
        if "value weighted" in line.lower() and "monthly" in line.lower():
            start = i
            break
    if start is None:
        start = 0

    # Find the header line (comma-separated, with portfolio names) after start
    header = None
    h_idx = None
    for i in range(start, len(lines)):
        if "," in lines[i] and not DATA_RE.match(lines[i]):
            parts = [p.strip() for p in lines[i].split(",")]
            names = [p.upper() for p in parts[1:]]
            if any("LOOP" in n or "HIOP" in n for n in names):
                header = parts[1:]
                h_idx = i
                break
    if header is None:
        raise SystemExit("Could not find header line")

    names = [h.upper() for h in header]

    def find_col(target):
        for j, n in enumerate(names):
            if n == target:
                return j
        return None

    c_sl = find_col("SMALL LOOP")
    c_sh = find_col("SMALL HIOP")
    c_bl = find_col("BIG LOOP")
    c_bh = find_col("BIG HIOP")
    if None in (c_sl, c_sh, c_bl, c_bh):
        # positional fallback: columns 1,3,4,6 (0-based 0,2,3,5)
        c_sl, c_sh, c_bl, c_bh = 0, 2, 3, 5

    # Collect data rows
    rows = {}
    started = False
    for i in range(h_idx + 1, len(lines)):
        line = lines[i]
        m = DATA_RE.match(line)
        if m:
            started = True
            date = int(m.group(1))
            fields = line.split(",")[1:]
            def get(c):
                if c < len(fields):
                    return to_float(fields[c])
                return float("nan")
            sl, sh, bl, bh = get(c_sl), get(c_sh), get(c_bl), get(c_bh)
            rows[date] = (sl, sh, bl, bh)
        else:
            if started:
                # End of monthly block
                break

    out = []
    for date in sorted(rows):
        sl, sh, bl, bh = rows[date]
        if any(math.isnan(v) for v in (sl, sh, bl, bh)):
            continue
        rmw = 0.5 * (sh + bh) - 0.5 * (sl + bl)
        out.append((date, rmw))

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("date,value\n")
        for date, v in out:
            f.write(f"{date},{v!r}\n")


if __name__ == "__main__":
    main()
