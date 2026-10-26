import re
import pandas as pd

FNAME = "6_Portfolios_2x3.csv"

with open(FNAME, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# locate the value-weighted monthly section
start = None
for i, ln in enumerate(lines):
    s = ln.strip().lower()
    if "value weighted returns" in s and "monthly" in s and "equal" not in s:
        start = i
        break
if start is None:
    raise RuntimeError("Value-weighted monthly section not found")

# header line
hdr_idx = start + 1
while hdr_idx < len(lines) and lines[hdr_idx].strip() == "":
    hdr_idx += 1
header = [h.strip() for h in lines[hdr_idx].split(",")]
cols = header[1:]

rows = []
date_re = re.compile(r"^\s*(\d{6})\s*$")
for ln in lines[hdr_idx + 1:]:
    parts = ln.split(",")
    if not parts or not date_re.match(parts[0]):
        break
    d = int(parts[0].strip())
    vals = []
    for p in parts[1:1 + len(cols)]:
        try:
            vals.append(float(p.strip()))
        except ValueError:
            vals.append(float("nan"))
    rows.append([d] + vals)

df = pd.DataFrame(rows, columns=["date"] + cols)

def find_col(keys):
    for c in cols:
        u = c.upper().replace(" ", "")
        if all(k in u for k in keys):
            return c
    raise KeyError(keys)

sl = find_col(["SMALL", "LOBM"])
sh = find_col(["SMALL", "HIBM"])
bl = find_col(["BIG", "LOBM"])
bh = find_col(["BIG", "HIBM"])

sub = df[["date", sl, sh, bl, bh]].copy()
for c in [sl, sh, bl, bh]:
    sub.loc[(sub[c] <= -99.99) | (sub[c] == -999), c] = float("nan")
sub = sub.dropna()

sub["value"] = 0.5 * (sub[sh] + sub[bh]) - 0.5 * (sub[sl] + sub[bl])
out = sub[["date", "value"]].copy()
out["date"] = out["date"].astype(int)
out["value"] = out["value"].round(4)
out = out.sort_values("date").drop_duplicates("date")
out.to_csv("output.csv", index=False)
