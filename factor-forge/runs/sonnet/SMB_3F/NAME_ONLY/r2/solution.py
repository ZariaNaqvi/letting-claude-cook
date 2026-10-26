import csv

rows = []
in_section = False
with open("6_Portfolios_2x3.csv", "r", errors="ignore") as f:
    for line in f:
        s = line.strip()
        if not in_section:
            if s.startswith("Average Value Weighted Returns") and "Monthly" in s:
                in_section = True
            continue
        if not s:
            if rows:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts) < 7:
            if rows:
                break
            continue
        d = parts[0]
        if not (d.isdigit() and len(d) == 6):
            if rows:
                break
            continue
        try:
            vals = [float(x) for x in parts[1:7]]
        except ValueError:
            continue
        rows.append((int(d), vals))

out = []
for d, v in rows:
    if any(x <= -99.99 or x == -999 for x in v):
        continue
    small = (v[0] + v[1] + v[2]) / 3.0
    big = (v[3] + v[4] + v[5]) / 3.0
    out.append((d, round(small - big, 4)))

with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, x in out:
        w.writerow([d, x])
