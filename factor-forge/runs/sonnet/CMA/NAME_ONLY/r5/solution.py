import pandas as pd

rows = []
started = False
with open("6_Portfolios_ME_INV_2x3.csv", "r", encoding="latin-1") as f:
    in_section = False
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
        if parts[0].isdigit() and len(parts[0]) == 6 and len(parts) >= 7:
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
bad = (df[["sl", "sm", "sh", "bl", "bm", "bh"]] <= -99).any(axis=1)
df = df[~bad]
df["value"] = 0.5 * (df["sl"] + df["bl"]) - 0.5 * (df["sh"] + df["bh"])
df[["date", "value"]].to_csv("output.csv", index=False)
