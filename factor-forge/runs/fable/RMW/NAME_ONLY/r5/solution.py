import re
import pandas as pd

fname = "6_Portfolios_ME_OP_2x3.csv"

with open(fname, "r") as f:
    lines = f.read().splitlines()

# Locate the first block: "Average Value Weighted Returns -- Monthly"
start = None
for i, ln in enumerate(lines):
    if "Average Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    # fallback: first block of data in file
    start = 0

rows = []
started = False
pat = re.compile(r"^\s*(\d{6})\s*,")
for ln in lines[start + 1:]:
    m = pat.match(ln)
    if m:
        started = True
        parts = [p.strip() for p in ln.split(",")]
        try:
            vals = [float(p) for p in parts[1:7]]
        except ValueError:
            continue
        rows.append([int(parts[0])] + vals)
    elif started:
        # end of block (blank line or next header)
        if ln.strip() == "" or not ln.strip()[0].isdigit():
            break

df = pd.DataFrame(rows, columns=["date", "SL", "SM", "SH", "BL", "BM", "BH"])

# Drop missing values (-99.99 / -999)
mask = (df[["SL", "SM", "SH", "BL", "BM", "BH"]] > -99).all(axis=1)
df = df[mask].copy()

# RMW = 1/2 (Small Robust + Big Robust) - 1/2 (Small Weak + Big Weak)
df["value"] = 0.5 * (df["SH"] + df["BH"]) - 0.5 * (df["SL"] + df["BL"])

out = df[["date", "value"]].copy()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
