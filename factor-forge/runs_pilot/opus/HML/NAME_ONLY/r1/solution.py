import csv
import re

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# locate the first monthly value-weighted section
start = None
for i, ln in enumerate(lines):
    s = ln.strip().lower()
    if "value weighted returns" in s and "monthly" in s:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly section not found")

# header line: next non-empty line starting with comma
j = start + 1
while j < len(lines) and not lines[j].strip():
    j += 1
header = [h.strip().upper() for h in lines[j].split(",")]

def find_col(pred):
    for k, h in enumerate(header):
        if pred(h):
            return k
    return None

sl = find_col(lambda h: ("SMALL" in h or "ME1" in h) and "LO" in h)
sh = find_col(lambda h: ("SMALL" in h or "ME1" in h) and "HI" in h)
bl = find_col(lambda h: ("BIG" in h or "ME2" in h) and "LO" in h)
bh = find_col(lambda h: ("BIG" in h or "ME2" in h) and "HI" in h)
if None in (sl, sh, bl, bh):
    # fall back to standard order
    sl, sh, bl, bh = 1, 3, 4, 6

rows = []
date_re = re.compile(r"^\d{6}$")
for ln in lines[j + 1:]:
    parts = [p.strip() for p in ln.split(",")]
    if not parts or not date_re.match(parts[0]):
        break
    try:
        vals = [float(parts[k]) for k in (sl, sh, bl, bh)]
    except (ValueError, IndexError):
        continue
    if any(v <= -99.99 + 1e-9 for v in vals):
        continue
    v_sl, v_sh, v_bl, v_bh = vals
    hml = 0.5 * (v_sh + v_bh) - 0.5 * (v_sl + v_bl)
    rows.append((int(parts[0]), hml))

with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in rows:
        w.writerow([d, f"{v:.6f}"])
