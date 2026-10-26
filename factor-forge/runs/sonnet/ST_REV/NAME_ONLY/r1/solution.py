import pandas as pd

rows = []
started = False
with open("6_Portfolios_ME_Prior_1_0.csv") as f:
    for line in f:
        s = line.strip()
        if not started:
            if s.startswith(",") and "SMALL" in s.upper() and "PRIOR" in s.upper():
                started = True
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts) >= 7 and len(parts[0]) == 6 and parts[0].isdigit():
            try:
                vals = [float(x) for x in parts[1:7]]
            except ValueError:
                continue
            rows.append([int(parts[0])] + vals)
        else:
            if rows:
                break

df = pd.DataFrame(rows, columns=["date", "sl", "sm", "sh", "bl", "bm", "bh"])
for c in ["sl", "sm", "sh", "bl", "bm", "bh"]:
    df.loc[df[c] <= -99.99, c] = float("nan")
df["value"] = 0.5 * (df["sl"] + df["bl"]) - 0.5 * (df["sh"] + df["bh"])
out = df.dropna(subset=["value"])[["date", "value"]]
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
