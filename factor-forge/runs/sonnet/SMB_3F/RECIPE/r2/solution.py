import csv

rows = []
started = False
with open("6_Portfolios_2x3.csv", "r", errors="replace") as f:
    for line in f:
        s = line.strip()
        if not started:
            if "Average Value Weighted Returns" in s and "Monthly" in s:
                started = True
            continue
        if not s:
            if rows:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        d = parts[0]
        if len(d) == 6 and d.isdigit() and len(parts) >= 7:
            try:
                vals = [float(x) for x in parts[1:7]]
            except ValueError:
                continue
            rows.append((int(d), vals))
        else:
            if rows:
                break

out = []
for d, v in rows:
    if any(x <= -99.0 for x in v):
        continue
    smb = sum(v[0:3]) / 3.0 - sum(v[3:6]) / 3.0
    out.append((d, smb))

with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, x in out:
        w.writerow([d, round(x, 6)])
