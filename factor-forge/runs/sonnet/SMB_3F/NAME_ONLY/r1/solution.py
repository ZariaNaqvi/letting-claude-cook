import pandas as pd

rows = []
in_section = False
started = False
with open("6_Portfolios_2x3.csv", "r", errors="ignore") as f:
    for line in f:
        s = line.strip()
        if not in_section:
            if "Average Value Weighted Returns" in s and "Monthly" in s:
                in_section = True
            continue
        if not s:
            if started:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts[0]) == 6 and parts[0].isdigit() and len(parts) >= 7:
            started = True
            try:
                vals = [float(x) for x in parts[1:7]]
            except ValueError:
                continue
            rows.append((int(parts[0]), vals))
        else:
            if started:
                break

out = []
for d, v in rows:
    if any(x <= -99.99 or x == -999 for x in v):
        continue
    small = (v[0] + v[1] + v[2]) / 3.0
    big = (v[3] + v[4] + v[5]) / 3.0
    out.append((d, round(small - big, 4)))

df = pd.DataFrame(out, columns=["date", "value"])
df["date"] = df["date"].astype(int)
df.to_csv("output.csv", index=False)
