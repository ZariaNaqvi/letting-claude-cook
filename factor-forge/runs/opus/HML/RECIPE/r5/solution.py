import csv
import math

FNAME = "6_Portfolios_2x3.csv"
TITLE = "Average Value Weighted Returns -- Monthly"

with open(FNAME, "r", newline="", encoding="latin-1") as f:
    lines = f.read().splitlines()

# locate first value-weighted monthly block
start = None
for i, ln in enumerate(lines):
    if TITLE.lower() in ln.lower():
        start = i
        break
if start is None:
    raise RuntimeError("Monthly value-weighted block not found")

# header line: next non-empty line
j = start + 1
while j < len(lines) and lines[j].strip() == "":
    j += 1
header = [h.strip() for h in next(csv.reader([lines[j]]))]
col = {name.upper(): k for k, name in enumerate(header)}

def find(name):
    key = name.upper()
    if key in col:
        return col[key]
    # fallback: normalize whitespace
    for k, v in col.items():
        if " ".join(k.split()) == key:
            return v
    raise KeyError(name)

i_sl = find("SMALL LoBM")
i_sh = find("SMALL HiBM")
i_bl = find("BIG LoBM")
i_bh = find("BIG HiBM")

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
        vals = [float(parts[k]) for k in (i_sl, i_sh, i_bl, i_bh)]
    except (ValueError, IndexError):
        continue
    if any(v <= -99.99 + 1e-9 or v == -999 or math.isnan(v) for v in vals):
        continue
    sl, sh, bl, bh = vals
    hml = 0.5 * (sh + bh) - 0.5 * (sl + bl)
    rows.append((int(d), hml))

rows.sort()
with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in rows:
        w.writerow([d, f"{v:.6f}"])
