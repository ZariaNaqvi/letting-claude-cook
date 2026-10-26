import csv
import math

FNAME = "6_Portfolios_ME_INV_2x3.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the first block: Average Value Weighted Returns -- Monthly
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# Header line is the next non-empty line
j = start + 1
while j < len(lines) and lines[j].strip() == "":
    j += 1
header = [h.strip() for h in next(csv.reader([lines[j]]))]
cols = {name.upper(): k for k, name in enumerate(header)}

def find_col(name, fallback):
    return cols.get(name.upper(), fallback)

i_sl = find_col("SMALL LoINV", 1)
i_sh = find_col("SMALL HiINV", 3)
i_bl = find_col("BIG LoINV", 4)
i_bh = find_col("BIG HiINV", 6)

def val(x):
    try:
        v = float(x)
    except ValueError:
        return math.nan
    if v <= -99.99 or v == -999:
        return math.nan
    return v

out = []
k = j + 1
while k < len(lines):
    ln = lines[k]
    if ln.strip() == "":
        break
    parts = [p.strip() for p in next(csv.reader([ln]))]
    d = parts[0]
    if not (d.isdigit() and len(d) == 6):
        break
    try:
        sl = val(parts[i_sl]); sh = val(parts[i_sh])
        bl = val(parts[i_bl]); bh = val(parts[i_bh])
    except IndexError:
        k += 1
        continue
    v = 0.5 * (sl + bl) - 0.5 * (sh + bh)
    if not math.isnan(v):
        out.append((int(d), v))
    k += 1

with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in out:
        w.writerow([d, f"{v:.6f}"])
