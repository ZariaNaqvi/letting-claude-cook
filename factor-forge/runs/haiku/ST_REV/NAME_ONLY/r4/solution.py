import re
import math
import csv

FN = "6_Portfolios_ME_Prior_1_0.csv"
OUT = "output.csv"
MISSING = {-99.99, -999.0, -999.99}
DATE_RE = re.compile(r'^\s*(\d{6})\s*,')


def to_num(s):
    try:
        v = float(s.strip())
    except ValueError:
        return float("nan")
    if v in MISSING or math.isclose(v, -99.99) or math.isclose(v, -999.0):
        return float("nan")
    return v


def main():
    with open(FN, encoding="latin-1") as f:
        lines = f.readlines()

    # Start searching at the "Value Weighted ... Monthly" block if present
    start = 0
    for i, l in enumerate(lines):
        if "value weighted" in l.lower() and "monthly" in l.lower():
            start = i
            break

    # Find first data row of that block
    first = None
    for i in range(start, len(lines)):
        if DATE_RE.match(lines[i]):
            first = i
            break
    if first is None:
        raise SystemExit("No data rows found")

    # Header: nearest preceding line containing commas and portfolio names
    header = None
    for i in range(first - 1, -1, -1):
        if "," in lines[i] and "SMALL" in lines[i].upper():
            header = [p.strip().upper() for p in lines[i].split(",")]
            break

    # Determine column indices (in value list, 0-based after date)
    idx_sl, idx_bl, idx_sh, idx_bh = 0, 3, 2, 5
    if header is not None:
        names = header[1:]  # drop the date column label
        found = {}
        for j, n in enumerate(names):
            if "SMALL" in n and "LO" in n:
                found["sl"] = j
            elif "BIG" in n and "LO" in n:
                found["bl"] = j
            elif "SMALL" in n and "HI" in n:
                found["sh"] = j
            elif "BIG" in n and "HI" in n:
                found["bh"] = j
        if len(found) == 4:
            idx_sl, idx_bl, idx_sh, idx_bh = found["sl"], found["bl"], found["sh"], found["bh"]

    # Collect the contiguous run of data rows
    rows = []
    for i in range(first, len(lines)):
        m = DATE_RE.match(lines[i])
        if not m:
            break
        parts = lines[i].rstrip("\r\n").split(",")
        date = int(parts[0].strip())
        vals = [to_num(p) for p in parts[1:]]
        if max(idx_sl, idx_bl, idx_sh, idx_bh) >= len(vals):
            continue
        sl = vals[idx_sl]
        bl = vals[idx_bl]
        sh = vals[idx_sh]
        bh = vals[idx_bh]
        if any(math.isnan(x) for x in (sl, bl, sh, bh)):
            continue
        st_rev = 0.5 * (sl + bl) - 0.5 * (sh + bh)
        rows.append((date, st_rev))

    # Deduplicate by date (keep first) and sort
    seen = {}
    for d, v in rows:
        if d not in seen:
            seen[d] = v
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "value"])
        for d in sorted(seen):
            w.writerow([d, repr(float(seen[d]))])


if __name__ == "__main__":
    main()
