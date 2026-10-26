import pandas as pd

rows = []
started = False
in_block = False
with open("6_Portfolios_ME_Prior_1_0.csv") as f:
    for line in f:
        s = line.strip()
        if not in_block:
            if "Value Weighted Returns" in s and "Monthly" in s:
                in_block = True
            continue
        if not s:
            if started:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if parts[0].isdigit() and len(parts[0]) == 6:
            started = True
            try:
                vals = [float(x) for x in parts[1:7]]
            except ValueError:
                continue
            rows.append([int(parts[0])] + vals)
        else:
            if started:
                break

df = pd.DataFrame(rows, columns=["date", "sl", "sm", "sh", "bl", "bm", "bh"])
for c in ["sl", "sm", "sh", "bl", "bm", "bh"]:
    df.loc[(df[c] <= -99.0), c] = float("nan")
df["value"] = 0.5 * (df["sl"] + df["bl"]) - 0.5 * (df["sh"] + df["bh"])
out = df.dropna(subset=["value"])[["date", "value"]].copy()
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
