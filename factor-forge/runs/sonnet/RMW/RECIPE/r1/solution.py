import re

rows = []
started = False
with open("6_Portfolios_ME_OP_2x3.csv", "r", errors="ignore") as f:
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
        if re.fullmatch(r"\d{6}", parts[0]) and len(parts) >= 7:
            try:
                vals = [float(x) for x in parts[1:7]]
            except ValueError:
                continue
            rows.append((int(parts[0]), vals))
        else:
            if rows:
                break

out = []
for d, v in rows:
    sl, _, sh, bl, _, bh = v
    if any(x <= -99.0 for x in (sl, sh, bl, bh)):
        continue
    out.append((d, round(0.5 * (sh + bh) - 0.5 * (sl + bl), 4)))

with open("output.csv", "w") as f:
    f.write("date,value\n")
    for d, val in out:
        f.write(f"{d},{val}\n")
