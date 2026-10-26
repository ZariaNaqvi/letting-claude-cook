import csv
import math

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate the first block: Average Value Weighted Returns -- Monthly
start = None
for i, line in enumerate(lines):
    if "Average Value Weighted Returns" in line and "Monthly" in line:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# Header line
hdr_idx = start + 1
while hdr_idx < len(lines) and lines[hdr_idx].strip() == "":
    hdr_idx += 1
header = [h.strip() for h in next(csv.reader([lines[hdr_idx]]))]
cols = {name.upper(): j for j, name in enumerate(header)}

def find_col(name):
    key = name.upper()
    if key in cols:
        return cols[key]
    # fallback: normalized match
    norm = lambda s: " ".join(s.upper().split())
    for k, j in cols.items():
        if norm(k) == norm(key):
            return j
    raise KeyError(name)

i_sl = find_col("SMALL LoBM")
i_sh = find_col("SMALL HiBM")
i_bl = find_col("BIG LoBM")
i_bh = find_col("BIG HiBM")

def parse(x):
    try:
        v = float(x.strip())
    except Exception:
        return None
    if v <= -99.99 or v == -999 or math.isnan(v):
        return None
    return v

out = []
for line in lines[hdr_idx + 1:]:
    if line.strip() == "":
        break
    row = next(csv.reader([line]))
    d = row[0].strip()
    if not (d.isdigit() and len(d) == 6):
        break
    try:
        vals = [parse(row[k]) for k in (i_sl, i_sh, i_bl, i_bh)]
    except IndexError:
        continue
    if any(v is None for v in vals):
        continue
    sl, sh, bl, bh = vals
    hml = 0.5 * (sh + bh) - 0.5 * (sl + bl)
    out.append((int(d), hml))

with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in out:
        w.writerow([d, f"{v:.6f}"])
