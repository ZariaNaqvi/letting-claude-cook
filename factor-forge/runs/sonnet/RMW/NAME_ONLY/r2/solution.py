import re
import pandas as pd

rows = []
started = False
with open("6_Portfolios_ME_OP_2x3.csv", "r", errors="ignore") as f:
    in_section = False
    for line in f:
        s = line.strip()
        if not in_section:
            if "Average Value Weighted Returns" in s and "Monthly" in s:
                in_section = True
            continue
        parts = [p.strip() for p in s.split(",")]
        if re.fullmatch(r"\d{6}", parts[0] or ""):
            started = True
            try:
                vals = [float(x) for x in parts[1:7]]
            except ValueError:
                continue
            rows.append([int(parts[0])] + vals)
        elif started:
            break

df = pd.DataFrame(rows, columns=["date", "sl", "s2", "sh", "bl", "b2", "bh"])
for c in ["sl", "sh", "bl", "bh"]:
    df.loc[df[c].isin([-99.99, -999, -999.0]), c] = float("nan")
df = df.dropna(subset=["sl", "sh", "bl", "bh"])
df["value"] = (df["sh"] + df["bh"]) / 2 - (df["sl"] + df["bl"]) / 2
df[["date", "value"]].to_csv("output.csv", index=False)
