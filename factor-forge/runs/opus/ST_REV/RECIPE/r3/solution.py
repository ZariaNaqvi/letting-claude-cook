import csv
import math

FNAME = "6_Portfolios_ME_Prior_1_0.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate first block: Average Value Weighted Returns -- Monthly
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# Header line: next non-empty line
j = start + 1
while j < len(lines) and lines[j].strip() == "":
    j += 1
header = [h.strip() for h in next(csv.reader([lines[j]]))]

def find_col(name):
    target = name.replace(" ", "").upper()
    for k, h in enumerate(header):
        if h.replace(" ", "").upper() == target:
            return k
    raise RuntimeError(f"Column {name} not found in header {header}")

c_sl = find_col("SMALL LoPRIOR")
c_sh = find_col("SMALL HiPRIOR")
c_bl = find_col("BIG LoPRIOR")
c_bh = find_col("BIG HiPRIOR")

rows = []
for ln in lines[j + 1:]:
    s = ln.strip()
    if s == "":
        break
    parts = [p.strip() for p in next(csv.reader([ln]))]
    d = parts[0]
    if not (d.isdigit() and len(d) == 6):
        break
    try:
        vals = [float(parts[c]) for c in (c_sl, c_sh, c_bl, c_bh)]
    except (ValueError, IndexError):
        continue
    if any(math.isnan(v) or v <= -99.99 + 1e-9 for v in vals):
        continue
    sl, sh, bl, bh = vals
    v = 0.5 * (sl + bl) - 0.5 * (sh + bh)
    rows.append((int(d), v))

rows.sort(key=lambda r: r[0])

with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in rows:
        w.writerow([d, f"{v:.6f}".rstrip("0").rstrip(".") if v != 0 else "0"])
