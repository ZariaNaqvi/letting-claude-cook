import csv
import math

rows = []
with open("6_Portfolios_ME_INV_2x3.csv", "r", encoding="latin-1") as f:
    lines = f.read().splitlines()

start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i + 1
        break
if start is None:
    start = 0

started = False
for l in lines[start:]:
    parts = [p.strip() for p in l.split(",")]
    if len(parts) >= 7 and parts[0].isdigit() and len(parts[0]) == 6:
        started = True
        try:
            v = [float(x) for x in parts[1:7]]
        except ValueError:
            continue
        if any(x <= -99.0 for x in v):
            continue
        sl, m1, sh, bl, m2, bh = v
        cma = 0.5 * (sl + bl) - 0.5 * (sh + bh)
        rows.append((int(parts[0]), cma))
    elif started:
        break

with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in rows:
        w.writerow([d, round(v, 6)])
