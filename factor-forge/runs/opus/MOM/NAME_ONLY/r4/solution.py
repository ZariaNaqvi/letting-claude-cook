import re
import numpy as np
import pandas as pd

FNAME = "6_Portfolios_ME_Prior_12_2.csv"

with open(FNAME, "r", encoding="latin-1") as f:
    lines = f.read().splitlines()

# locate first value-weighted monthly section
start = None
for i, ln in enumerate(lines):
    if "Value Weighted Returns" in ln and "Monthly" in ln:
        start = i
        break
if start is None:
    # fallback: first header line starting with comma
    for i, ln in enumerate(lines):
        if ln.strip().startswith(","):
            start = i - 1
            break

# header line
hdr_idx = start + 1
while not lines[hdr_idx].strip().startswith(","):
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")][1:]

rows = []
pat = re.compile(r"^\s*(\d{6})\s*,")
for ln in lines[hdr_idx + 1:]:
    m = pat.match(ln)
    if not m:
        break
    parts = [p.strip() for p in ln.split(",")]
    date = int(parts[0])
    vals = []
    for p in parts[1:1 + len(header)]:
        try:
            vals.append(float(p))
        except ValueError:
            vals.append(np.nan)
    rows.append([date] + vals)

df = pd.DataFrame(rows, columns=["date"] + header)
data = df[header].astype(float)
data = data.mask((data <= -99.99 + 1e-9) & (data >= -99.99 - 1e-9))
data = data.mask(data <= -999 + 1e-9)


def find_col(size_keys, prior_key, fallback_idx):
    for c in header:
        cu = c.upper().replace(" ", "")
        if any(k in cu for k in size_keys) and prior_key in cu:
            return c
    return header[fallback_idx]


sl = find_col(["SMALL", "ME1"], "LOPRIOR", 0)
sh = find_col(["SMALL", "ME1"], "HIPRIOR", 2)
bl = find_col(["BIG", "ME2"], "LOPRIOR", 3)
bh = find_col(["BIG", "ME2"], "HIPRIOR", 5)

mom = 0.5 * (data[sh] + data[bh]) - 0.5 * (data[sl] + data[bl])

out = pd.DataFrame({"date": df["date"].astype(int), "value": mom})
out = out.dropna().drop_duplicates("date").sort_values("date")
out["value"] = out["value"].round(4)
out.to_csv("output.csv", index=False)
