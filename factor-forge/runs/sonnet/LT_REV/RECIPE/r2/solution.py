import math

fn = "6_Portfolios_ME_Prior_60_13.csv"
with open(fn, "r", encoding="latin-1") as f:
    lines = f.read().splitlines()

start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l:
        start = i
        break

header = [h.strip() for h in lines[start + 1].split(",")]
idx = {h: j for j, h in enumerate(header)}
need = ["SMALL LoPRIOR", "SMALL HiPRIOR", "BIG LoPRIOR", "BIG HiPRIOR"]
ci = {k: idx[k] for k in need}

def val(x):
    try:
        v = float(x)
    except ValueError:
        return float("nan")
    if v <= -99.99 or v == -999:
        return float("nan")
    return v

rows = []
started = False
for l in lines[start + 2:]:
    parts = [p.strip() for p in l.split(",")]
    d = parts[0]
    if len(d) == 6 and d.isdigit():
        started = True
        try:
            sl = val(parts[ci["SMALL LoPRIOR"]])
            sh = val(parts[ci["SMALL HiPRIOR"]])
            bl = val(parts[ci["BIG LoPRIOR"]])
            bh = val(parts[ci["BIG HiPRIOR"]])
        except IndexError:
            continue
        v = 0.5 * (sl + bl) - 0.5 * (sh + bh)
        if not math.isnan(v):
            rows.append((int(d), v))
    elif started:
        break

with open("output.csv", "w") as f:
    f.write("date,value\n")
    for d, v in rows:
        f.write(f"{d},{round(v, 6)}\n")
