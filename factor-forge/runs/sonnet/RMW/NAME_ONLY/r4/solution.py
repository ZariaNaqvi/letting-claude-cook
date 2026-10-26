import pandas as pd

rows = []
in_section = False
started = False
with open("6_Portfolios_ME_OP_2x3.csv", "r", errors="ignore") as f:
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
        if parts[0].isdigit() and len(parts[0]) == 6:
            started = True
            try:
                vals = [float(x) for x in parts[1:7]]
            except ValueError:
                continue
            rows.append([int(parts[0])] + vals)
        elif started:
            break

df = pd.DataFrame(rows, columns=["date", "sl", "sm", "sh", "bl", "bm", "bh"])
for c in ["sl", "sm", "sh", "bl", "bm", "bh"]:
    df.loc[(df[c] <= -99.0), c] = float("nan")
df = df.dropna()
df["value"] = ((df["sh"] + df["bh"]) - (df["sl"] + df["bl"])) / 2.0
df[["date", "value"]].to_csv("output.csv", index=False)
