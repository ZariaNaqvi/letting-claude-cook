import csv
import math

def main():
    with open("6_Portfolios_ME_Prior_60_13.csv", "r", encoding="latin-1") as f:
        lines = f.read().splitlines()

    start = None
    for i, l in enumerate(lines):
        if "SMALL LoPRIOR" in l and "BIG" in l:
            start = i
            break
    header = [h.strip() for h in lines[start].split(",")]
    idx = {h: j for j, h in enumerate(header)}
    a = idx["SMALL LoPRIOR"]
    b = idx["BIG LoPRIOR"]
    c = idx["SMALL HiPRIOR"]
    d = idx["BIG HiPRIOR"]

    rows = []
    for l in lines[start + 1:]:
        parts = [p.strip() for p in l.split(",")]
        if not parts or not (len(parts[0]) == 6 and parts[0].isdigit()):
            break
        try:
            vals = [float(x) for x in parts[1:]]
        except ValueError:
            continue
        # header has leading empty field, so index j in header -> parts[j]
        try:
            sl = float(parts[a]); bl = float(parts[b])
            sh = float(parts[c]); bh = float(parts[d])
        except (ValueError, IndexError):
            continue
        if any(v <= -99.99 or v == -999 for v in (sl, bl, sh, bh)):
            continue
        val = 0.5 * (sl + bl) - 0.5 * (sh + bh)
        rows.append((int(parts[0]), val))

    with open("output.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "value"])
        for dt, v in rows:
            w.writerow([dt, repr(round(v, 6))])

main()
