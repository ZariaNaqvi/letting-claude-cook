import csv

rows = []
started = False
with open("6_Portfolios_2x3.csv", "r", errors="ignore") as f:
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
        if len(d) == 6 and d.isdigit():
            try:
                v = [float(x) for x in parts[1:7]]
            except ValueError:
                continue
            if len(v) < 6:
                continue
            if any(x <= -99.99 for x in v):
                continue
            hml = 0.5 * (v[2] + v[5]) - 0.5 * (v[0] + v[3])
            rows.append((int(d), round(hml, 6)))
        else:
            if rows:
                break

with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in rows:
        w.writerow([d, v])
