import re
import numpy as np
import pandas as pd

FILE = "6_Portfolios_ME_Prior_60_13.csv"
OUT = "output.csv"

def is_missing(v):
    return (abs(v + 99.99) < 1e-6) or (abs(v + 999.0) < 1e-6)

with open(FILE, encoding="latin-1") as f:
    lines = f.read().splitlines()

# locate the first monthly value-weighted block
start = None
for i, l in enumerate(lines):
    if "Average Value Weighted Returns" in l and "Monthly" in l:
        start = i
        break
if start is None:
    raise SystemExit("Monthly value-weighted block not found")

# header line: first line after title starting with ','
hdr_idx = None
for j in range(start + 1, len(lines)):
    if lines[j].strip().startswith(","):
        hdr_idx = j
        break
header = [h.strip() for h in lines[hdr_idx].split(",")]

def col(name):
    return header.index(name)

c_SL = col("SMALL LoPRIOR")
c_SH = col("SMALL HiPRIOR")
c_BL = col("BIG LoPRIOR")
c_BH = col("BIG HiPRIOR")

records = []
started = False
for line in lines[hdr_idx + 1:]:
    s = line.strip()
    if not s:
        if started:
            break
        continue
    parts = [p.strip() for p in s.split(",")]
    if re.fullmatch(r"\d{6}", parts[0]):
        started = True
        try:
            vals = {}
            for key, c in (("SL", c_SL), ("SH", c_SH), ("BL", c_BL), ("BH", c_BH)):
                v = float(parts[c])
                vals[key] = np.nan if is_missing(v) else v
            records.append((int(parts[0]), vals))
        except (ValueError, IndexError):
            records.append((int(parts[0]), {"SL": np.nan, "SH": np.nan, "BL": np.nan, "BH": np.nan}))
    else:
        if started:
            break

rows = []
for date, v in records:
    lt = 0.5 * (v["SL"] + v["BL"]) - 0.5 * (v["SH"] + v["BH"])
    if np.isfinite(lt):
        rows.append((date, lt))

out = pd.DataFrame(rows, columns=["date", "value"])
out["date"] = out["date"].astype(int)
out.to_csv(OUT, index=False)
print(f"Wrote {len(out)} rows to {OUT}")
