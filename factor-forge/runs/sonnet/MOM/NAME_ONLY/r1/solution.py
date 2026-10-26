import pandas as pd

rows = []
started = False
with open("6_Portfolios_ME_Prior_12_2.csv", "r", errors="ignore") as f:
    for line in f:
        parts = [p.strip() for p in line.strip().split(",")]
        ok = len(parts) >= 7 and parts[0].isdigit() and len(parts[0]) == 6
        if ok:
            started = True
            rows.append(parts[:7])
        elif started:
            break

df = pd.DataFrame(rows, columns=["date", "sl", "sm", "sh", "bl", "bm", "bh"])
df["date"] = df["date"].astype(int)
for c in ["sl", "sm", "sh", "bl", "bm", "bh"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[df[c] <= -99.99, c] = float("nan")
df = df.dropna()
df["value"] = 0.5 * (df["sh"] + df["bh"]) - 0.5 * (df["sl"] + df["bl"])
df[["date", "value"]].to_csv("output.csv", index=False)
