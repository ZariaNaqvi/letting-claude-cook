import csv
import math

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the first value-weighted monthly block
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# Find header line (next non-empty line)
j = start + 1
while j < len(lines) and lines[j].strip() == "":
    j += 1
header = [h.strip() for h in lines[j].split(",")]
cols = {name.upper(): k for k, name in enumerate(header)}

def col(name):
    key = name.upper()
    if key in cols:
        return cols[key]
    # fallback: normalize whitespace
    for k, v in cols.items():
        if " ".join(k.split()) == key:
            return v
    raise KeyError(name)

i_sl = col("SMALL LoBM")
i_sh = col("SMALL HiBM")
i_bl = col("BIG LoBM")
i_bh = col("BIG HiBM")

def parse(x):
    try:
        v = float(x.strip())
    except Exception:
        return math.nan
    if v <= -99.99 + 1e-9 and (abs(v + 99.99) < 1e-6 or abs(v + 999) < 1e-6):
        return math.nan
    return v

out = []
seen = set()
j += 1
while j < len(lines):
    ln = lines[j]
    parts = ln.split(",")
    d = parts[0].strip()
    if not (len(d) == 6 and d.isdigit()):
        break
    try:
        sl = parse(parts[i_sl]); sh = parse(parts[i_sh])
        bl = parse(parts[i_bl]); bh = parse(parts[i_bh])
    except IndexError:
        j += 1
        continue
    if not any(math.isnan(v) for v in (sl, sh, bl, bh)):
        val = 0.5 * (sh + bh) - 0.5 * (sl + bl)
        di = int(d)
        if di not in seen:
            seen.add(di)
            out.append((di, val))
    j += 1

out.sort()
with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in out:
        w.writerow([d, round(v, 6)])
