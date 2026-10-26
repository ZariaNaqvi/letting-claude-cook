import csv

fn = "6_Portfolios_ME_OP_2x3.csv"
with open(fn, newline="", encoding="latin-1") as f:
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
    parts = [p.strip() for p in l.split(",")]
    if header is None:
        if "SMALL" in l.upper() and "HiOP" in l:
            header = parts
        i += 1
        continue
    if len(parts) > 1 and len(parts[0]) == 6 and parts[0].isdigit():
        rows.append(parts)
    else:
        if rows or not l.strip():
            if rows:
                break
    i += 1

idx = {name: header.index(name) for name in ["SMALL LoOP", "SMALL HiOP", "BIG LoOP", "BIG HiOP"]}

def bad(v):
    return v <= -99.0

out = []
for r in rows:
    try:
        sl = float(r[idx["SMALL LoOP"]])
        sh = float(r[idx["SMALL HiOP"]])
        bl = float(r[idx["BIG LoOP"]])
        bh = float(r[idx["BIG HiOP"]])
    except ValueError:
        continue
    if any(bad(v) for v in (sl, sh, bl, bh)):
        continue
    val = 0.5 * (sh + bh) - 0.5 * (sl + bl)
    out.append((int(r[0]), round(val, 6)))

with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in out:
        w.writerow([d, v])
