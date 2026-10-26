import re
import numpy as np
import pandas as pd

SRC = "6_Portfolios_2x3.csv"
OUT = "output.csv"

with open(SRC, encoding="latin-1") as f:
    lines = f.read().splitlines()

# Locate the first value-weighted monthly block
start = None
for i, line in enumerate(lines):
    low = line.lower()
    if "value weighted" in low and "monthly" in low:
        start = i
        break
if start is None:
    raise SystemExit("Could not find monthly value-weighted block")

# Header line follows the title (skip blank lines defensively)
j = start + 1
while j < len(lines) and lines[j].strip() == "":
    j += 1
header = [re.sub(r"\s+", " ", c.strip()) for c in lines[j].split(",")]
col_names = header[1:]

rows = []
started = False
for line in lines[j + 1:]:
    s = line.strip()
    if s == "":
        if started:
            break
        continue
    parts = [p.strip() for p in s.split(",")]
    if re.fullmatch(r"\d{6}", parts[0]):
        started = True
        vals = []
        for p in parts[1:1 + len(col_names)]:
            try:
                v = float(p)
            except ValueError:
                v = np.nan
            if v <= -99:  # -99.99 / -999 missing markers
                v = np.nan
            vals.append(v)
        while len(vals) < len(col_names):
            vals.append(np.nan)
        rows.append([int(parts[0])] + vals)
    else:
        if started:
            break

df = pd.DataFrame(rows, columns=["date"] + col_names)

needed = ["SMALL HiBM", "BIG HiBM", "SMALL LoBM", "BIG LoBM"]
for c in needed:
    if c not in df.columns:
        raise SystemExit(f"Missing column: {c}")

df = df.dropna(subset=needed).copy()
df["value"] = 0.5 * (df["SMALL HiBM"] + df["BIG HiBM"]) - 0.5 * (df["SMALL LoBM"] + df["BIG LoBM"])

out = df[["date", "value"]].copy()
out["date"] = out["date"].astype(int)
out.to_csv(OUT, index=False)
