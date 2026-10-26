import csv

rows = []
started = False
with open("6_Portfolios_ME_INV_2x3.csv", newline="") as f:
    for parts in csv.reader(f):
        if not parts:
            if started:
                break
            continue
        first = parts[0].strip()
        if first.isdigit() and len(first) == 6:
            started = True
            try:
                v = [float(x) for x in parts[1:7]]
            except ValueError:
                continue
            if len(v) < 6:
                continue
            if any(x <= -99.0 for x in (v[0], v[2], v[3], v[5])):
                continue
            val = 0.5 * (v[0] + v[3]) - 0.5 * (v[2] + v[5])
            rows.append((int(first), round(val, 6)))
        else:
            if started:
                break

with open("output.csv", "w") as f:
    f.write("date,value\n")
    for d, v in rows:
        f.write(f"{d},{v}\n")
