import csv

def main():
    with open("6_Portfolios_2x3.csv", "r", encoding="latin-1") as f:
        lines = f.read().splitlines()
    start = None
    for i, l in enumerate(lines):
        if "Average Value Weighted Returns" in l and "Monthly" in l:
            start = i
            break
    hdr = [h.strip() for h in lines[start + 1].split(",")]
    idx = {h: j for j, h in enumerate(hdr)}
    sh, bh = idx["SMALL HiBM"], idx["BIG HiBM"]
    sl, bl = idx["SMALL LoBM"], idx["BIG LoBM"]
    rows = []
    for l in lines[start + 2:]:
        parts = [p.strip() for p in l.split(",")]
        if not parts or not (len(parts[0]) == 6 and parts[0].isdigit()):
            break
        try:
            vals = [float(parts[j]) for j in (sh, bh, sl, bl)]
        except ValueError:
            continue
        if any(v <= -99.0 for v in vals):
            continue
        v = 0.5 * (vals[0] + vals[1]) - 0.5 * (vals[2] + vals[3])
        rows.append((int(parts[0]), round(v, 6)))
    with open("output.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "value"])
        w.writerows(rows)

main()
