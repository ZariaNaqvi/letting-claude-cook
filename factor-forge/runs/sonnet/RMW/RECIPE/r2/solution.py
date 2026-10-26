import re
import pandas as pd

rows = []
started = False
cols = None
with open("6_Portfolios_ME_OP_2x3.csv", "r", encoding="latin-1") as f:
    lines = f.read().splitlines()

i = 0
for idx, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        i = idx + 1
        break

# header row
while i < len(lines) and not lines[i].strip():
    i += 1
cols = [c.strip() for c in lines[i].split(",")]
i += 1
for l in lines[i:]:
    parts = [p.strip() for p in l.split(",")]
    if re.fullmatch(r"\d{6}", parts[0]):
        started = True
        rows.append(parts)
    else:
        if started:
            break
        if not l.strip():
            continue

df = pd.DataFrame(rows)
df = df.iloc[:, :len(cols)]
df.columns = ["date"] + cols[1:len(df.columns)]
df["date"] = df["date"].astype(int)
for c in df.columns[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df.loc[(df[c] <= -99.99) | (df[c] == -999), c] = float("nan")

val = 0.5 * (df["SMALL HiOP"] + df["BIG HiOP"]) - 0.5 * (df["SMALL LoOP"] + df["BIG LoOP"])
out = pd.DataFrame({"date": df["date"], "value": val}).dropna()
out["date"] = out["date"].astype(int)
out.to_csv("output.csv", index=False)
