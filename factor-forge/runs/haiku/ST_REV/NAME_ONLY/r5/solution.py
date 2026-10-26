import csv
import math
import re

INPUT = "6_Portfolios_ME_Prior_1_0.csv"
OUTPUT = "output.csv"

MISSING_VALUES = (-99.99, -999.0)


def norm(s):
    return re.sub(r"\s+", " ", s.strip())


def is_missing(x):
    if x is None or math.isnan(x):
        return True
    for m in MISSING_VALUES:
        if abs(x - m) < 1e-9:
            return True
    return False


def to_float(s):
    try:
        return float(s.strip())
    except (ValueError, AttributeError):
        return float("nan")


def main():
    header = None
    col = {}
    data = []  # list of (yyyymm, list of floats)
    started = False

    with open(INPUT, newline="") as f:
        reader = csv.reader(f)
        for parts in reader:
            if not parts or all(p.strip() == "" for p in parts):
                if started:
                    break  # end of first table block
                continue
            first = parts[0].strip()
            if header is None:
                names = [norm(p) for p in parts]
                if "SMALL LoPRIOR" in names:
                    header = names
                    for i, nm in enumerate(names):
                        col[nm] = i
                continue
            if re.fullmatch(r"\d{6}", first):
                started = True
                data.append((int(first), parts))
            else:
                if started:
                    break  # first table ended; ignore subsequent sections

    if header is None:
        raise RuntimeError("Could not locate value-weighted header row")

    need = ["SMALL LoPRIOR", "BIG LoPRIOR", "SMALL HiPRIOR", "BIG HiPRIOR"]
    for nm in need:
        if nm not in col:
            raise RuntimeError(f"Missing column {nm}")

    results = []
    for ym, parts in data:
        vals = {}
        for nm in need:
            idx = col[nm]
            v = to_float(parts[idx]) if idx < len(parts) else float("nan")
            vals[nm] = float("nan") if is_missing(v) else v
        if any(math.isnan(vals[nm]) for nm in need):
            continue
        st = 0.5 * (vals["SMALL LoPRIOR"] + vals["BIG LoPRIOR"]) \
            - 0.5 * (vals["SMALL HiPRIOR"] + vals["BIG HiPRIOR"])
        results.append((ym, st))

    results.sort(key=lambda x: x[0])

    with open(OUTPUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "value"])
        for ym, v in results:
            w.writerow([ym, repr(float(v))])


if __name__ == "__main__":
    main()
