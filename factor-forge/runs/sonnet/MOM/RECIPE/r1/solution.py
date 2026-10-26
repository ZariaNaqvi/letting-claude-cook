import csv

fn = "6_Portfolios_ME_Prior_12_2.csv"
with open(fn, newline="", encoding="latin-1") as f:
    lines = f.read().splitlines()

start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break

header = [h.strip() for h in lines[start + 1].split(",")]
idx = {h: j for j, h in enumerate(header)}
cSL = idx["SMALL LoPRIOR"]
cSH = idx["SMALL HiPRIOR"]
cBL = idx["BIG LoPRIOR"]
cBH = idx["BIG HiPRIOR"]

rows = []
seen = False
for l in lines[start + 2:]:
    parts = [p.strip() for p in l.split(",")]
    if parts and len(parts[0]) == 6 and parts[0].isdigit():
        seen = True
        try:
            sl, sh, bl, bh = (float(parts[c]) for c in (cSL, cSH, cBL, cBH))
        except (ValueError, IndexError):
            continue
        if any(v <= -99.0 for v in (sl, sh, bl, bh)):
            continue
        val = 0.5 * (sh + bh) - 0.5 * (sl + bl)
        rows.append((int(parts[0]), round(val, 4)))
    else:
        if seen:
            break

with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in rows:
        w.writerow([d, v])
