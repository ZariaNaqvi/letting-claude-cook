import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Locate first block: Average Value Weighted Returns -- Monthly
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly block not found")

# Header line is the next non-empty line
j = start + 1
while j < len(lines) and lines[j].strip() == "":
    j += 1
header = [h.strip() for h in lines[j].split(",")]
cols = header[1:]
j += 1

rows = []
date_re = re.compile(r"^\d{6}$")
while j < len(lines):
    ln = lines[j].strip()
    if ln == "":
        break
    parts = [p.strip() for p in ln.split(",")]
    if not date_re.match(parts[0]):
        break
    vals = []
    for p in parts[1:1 + len(cols)]:
        try:
            vals.append(float(p))
        except ValueError:
            vals.append(np.nan)
    rows.append([int(parts[0])] + vals)
    j += 1

df = pd.DataFrame(rows, columns=["date"] + cols)
for c in cols:
    df.loc[df[c] <= -99.99, c] = np.nan

def find(name):
    for c in cols:
        if c.replace(" ", "").upper() == name.replace(" ", "").upper():
            return c
    raise KeyError(name)

small = [find("SMALL LoBM"), find("ME1 BM2"), find("SMALL HiBM")]
big = [find("BIG LoBM"), find("ME2 BM2"), find("BIG HiBM")]

need = small + big
df = df.dropna(subset=need)
df["value"] = df[small].mean(axis=1) - df[big].mean(axis=1)

out = df[["date", "value"]].copy()
out["date"] = out["date"].astype(int)
out = out.sort_values("date").drop_duplicates("date")
out.to_csv("output.csv", index=False)
