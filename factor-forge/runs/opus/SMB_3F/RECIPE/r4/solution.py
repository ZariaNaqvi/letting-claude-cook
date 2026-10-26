import csv
import math

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# locate first block
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns -- Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# header line
h = start + 1
while not lines[h].strip():
    h += 1
header = [c.strip() for c in lines[h].split(",")]
cols = header[1:]

def idx(name):
    for k, c in enumerate(cols):
        if c.replace(" ", "").upper() == name.replace(" ", "").upper():
            return k
    raise RuntimeError(f"column {name} not found in {cols}")

small = [idx("SMALL LoBM"), idx("ME1 BM2"), idx("SMALL HiBM")]
big = [idx("BIG LoBM"), idx("ME2 BM2"), idx("BIG HiBM")]

rows = []
for ln in lines[h + 1:]:
    s = ln.strip()
    if not s:
        break
    parts = [p.strip() for p in s.split(",")]
    d = parts[0]
    if not (d.isdigit() and len(d) == 6):
        break
    try:
        vals = [float(p) for p in parts[1:]]
    except ValueError:
        continue
    needed = small + big
    if any(k >= len(vals) for k in needed):
        continue
    if any(vals[k] <= -99.99 + 1e-9 or vals[k] == -999 or math.isnan(vals[k]) for k in needed):
        continue
    smb = sum(vals[k] for k in small) / 3.0 - sum(vals[k] for k in big) / 3.0
    rows.append((int(d), smb))

with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in rows:
        w.writerow([d, round(v, 6)])
