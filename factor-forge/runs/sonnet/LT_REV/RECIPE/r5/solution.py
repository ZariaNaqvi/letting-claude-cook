import csv
import math

path = "6_Portfolios_ME_Prior_60_13.csv"
rows = []
header = None
started = False
with open(path, newline="", encoding="latin-1") as f:
    for line in f:
        s = line.strip()
        if header is None:
            if "SMALL LoPRIOR" in s:
                header = [h.strip() for h in s.split(",")]
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts[0]) == 6 and parts[0].isdigit():
            started = True
            rows.append(parts)
        else:
            if started:
                break

idx = {name: i for i, name in enumerate(header)}
cols = ["SMALL LoPRIOR", "BIG LoPRIOR", "SMALL HiPRIOR", "BIG HiPRIOR"]
ci = [idx[c] for c in cols]

def bad(v):
    return v <= -99.0

out = []
for r in rows:
    try:
        vals = [float(r[i]) for i in ci]
    except (ValueError, IndexError):
        continue
    if any(bad(v) for v in vals):
        continue
    sl, bl, sh, bh = vals
    val = 0.5 * (sl + bl) - 0.5 * (sh + bh)
    out.append((int(r[0]), val))

with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in out:
        w.writerow([d, round(v, 6)])
