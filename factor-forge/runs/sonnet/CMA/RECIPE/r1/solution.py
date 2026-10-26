import csv

rows = []
started = False
with open("6_Portfolios_ME_INV_2x3.csv", newline="") as f:
    in_block = False
    for line in f:
        s = line.strip()
        if not in_block:
            if s.startswith("Average Value Weighted Returns") and "Monthly" in s:
                in_block = True
            continue
        if not s:
            if started:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        first = parts[0]
        if len(first) == 6 and first.isdigit():
            started = True
            try:
                v = [float(x) for x in parts[1:7]]
            except ValueError:
                continue
            if any(x <= -99.0 for x in v):
                continue
            lo_s, _, hi_s, lo_b, _, hi_b = v
            val = 0.5 * (lo_s + lo_b) - 0.5 * (hi_s + hi_b)
            rows.append((int(first), round(val, 6)))
        else:
            if started:
                break

with open("output.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "value"])
    for d, v in rows:
        w.writerow([d, v])
