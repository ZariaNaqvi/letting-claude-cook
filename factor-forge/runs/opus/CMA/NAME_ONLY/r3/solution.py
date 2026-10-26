import csv
import math

FNAME = "6_Portfolios_ME_INV_2x3.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# locate the value-weighted monthly section
start = None
for i, ln in enumerate(lines):
    s = ln.strip().lower()
    if "average value weighted returns" in s and "monthly" in s:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly section not found")

# header line
hdr_idx = start + 1
while lines[hdr_idx].strip() == "":
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]
cols = header[1:]

def find_col(pred):
    for j, c in enumerate(cols):
        if pred(c.upper().replace(" ", "")):
            return j
    raise RuntimeError("column not found")

i_sl = find_col(lambda c: c.startswith("SMALL") and "LO" in c)
i_sh = find_col(lambda c: c.startswith("SMALL") and "HI" in c)
i_bl = find_col(lambda c: c.startswith("BIG") and "LO" in c)
i_bh = find_col(lambda c: c.startswith("BIG") and "HI" in c)

rows = []
for ln in lines[hdr_idx + 1:]:
    s = ln.strip()
    if s == "":
        break
    parts = [p.strip() for p in s.split(",")]
    d = parts[0]
    if not (d.isdigit() and len(d) == 6):
        break
    try:
        vals = [float(p) for p in parts[1:]]
    except ValueError:
        continue
    need = [vals[i_sl], vals[i_sh], vals[i_bl], vals[i_bh]]
    if any(v <= -99.99 or math.isnan(v) for v in need):
        continue
    cma = 0.5 * (vals[i_sl] + vals[i_bl]) - 0.5 * (vals[i_sh] + vals[i_bh])
    rows.append((int(d), round(cma, 4)))

with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in rows:
        w.writerow([d, v])
