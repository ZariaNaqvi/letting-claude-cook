import re
import csv

FILE = "6_Portfolios_ME_INV_2x3.csv"
OUT = "output.csv"


def norm(s):
    return re.sub(r"\s+", " ", s.strip()).upper()


def to_float(tok):
    try:
        v = float(tok)
    except (TypeError, ValueError):
        return float("nan")
    if v in (-99.99, -999.0) or v != v:
        return float("nan")
    return v


def main():
    with open(FILE, encoding="latin-1") as f:
        lines = f.readlines()

    # locate first (value-weighted, monthly) block
    start = None
    for i, l in enumerate(lines):
        if "Value Weighted Returns" in l and "Monthly" in l:
            start = i
            break
    if start is None:
        raise RuntimeError("Monthly value-weighted block not found")

    # header line: first non-empty line after the title
    j = start + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    header = [norm(h) for h in lines[j].strip().split(",")]

    want = {
        "SMALL LOINV": None,
        "BIG LOINV": None,
        "SMALL HIINV": None,
        "BIG HIINV": None,
    }
    for idx, h in enumerate(header):
        if h in want:
            want[h] = idx
    missing = [k for k, v in want.items() if v is None]
    if missing:
        raise RuntimeError(f"Missing columns: {missing}")

    rows = []
    for l in lines[j + 1:]:
        parts = [p.strip() for p in l.strip().split(",")]
        if not parts or not re.fullmatch(r"\d{6}", parts[0] or ""):
            break  # end of the monthly block
        date = int(parts[0])

        def get(name):
            k = want[name]
            return to_float(parts[k]) if k < len(parts) else float("nan")

        sl = get("SMALL LOINV")
        bl = get("BIG LOINV")
        sh = get("SMALL HIINV")
        bh = get("BIG HIINV")
        vals = (sl, bl, sh, bh)
        if any(v != v for v in vals):
            continue
        cma = 0.5 * (sl + bl) - 0.5 * (sh + bh)
        rows.append((date, cma))

    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "value"])
        for d, v in rows:
            w.writerow([d, f"{v:.6f}"])


if __name__ == "__main__":
    main()
