import csv
import math

fn = "6_Portfolios_ME_Prior_60_13.csv"
with open(fn, "r", encoding="latin-1") as f:
    lines = f.read().splitlines()

start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break

header = None
rows = []
i = start + 1
while i < len(lines):
    l = lines[i]
    if header is None:
        if l.strip().startswith(",") or "LoPRIOR" in l:
            header = [h.strip() for h in l.split(",")]
        i += 1
        continue
    parts = [p.strip() for p in l.split(",")]
    if len(parts) < 2 or not (parts[0].isdigit() and len(parts[0]) == 6):
        if rows:
            break
        i += 1
        continue
    rows.append(parts)
    i += 1

idx = {h: j for j, h in enumerate(header)}
cs = idx["SMALL LoPRIOR"]
cb = idx["BIG LoPRIOR"]
hs = idx["SMALL HiPRIOR"]
hb = idx["BIG HiPRIOR"]

def ok(v):
    return not (abs(v - (-99.99)) < 1e-6 or abs(v - (-999)) < 1e-6)

out = []
for p in rows:
    try:
        a, b, c, d = (float(p[cs]), float(p[cb]), float(p[hs]), float(p[hb]))
    except (ValueError, IndexError):
        continue
    if not all(ok(x) for x in (a, b, c, d)):
        continue
    val = 0.5 * (a + b) - 0.5 * (c + d)
    out.append((int(p[0]), val))

with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in out:
        w.writerow([d, repr(round(v, 6))])
