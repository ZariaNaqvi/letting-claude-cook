import pandas as pd
import numpy as np

def parse_monthly_vw(path):
    with open(path, "r", encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the first "Average Value Weighted Returns -- Monthly" section
    start = None
    for i, ln in enumerate(lines):
        if "Average Value Weighted Returns" in ln and "Monthly" in ln:
            start = i
            break
    if start is None:
        # Fallback: first section with a header line starting with a comma
        for i, ln in enumerate(lines):
            if ln.startswith(","):
                start = i - 1
                break

    # Find header line (starts with comma) after the section title
    j = start + 1
    while j < len(lines) and not lines[j].strip().startswith(","):
        j += 1
    header = [h.strip() for h in lines[j].split(",")]
    cols = header[1:]

    rows = []
    k = j + 1
    while k < len(lines):
        ln = lines[k].strip()
        if ln == "":
            # blank line ends the section (but tolerate blank only if we've already read data)
            if rows:
                break
            k += 1
            continue
        parts = [p.strip() for p in ln.split(",")]
        if not (len(parts[0]) == 6 and parts[0].isdigit()):
            break
        try:
            vals = [float(x) for x in parts[1:1 + len(cols)]]
        except ValueError:
            break
        rows.append([int(parts[0])] + vals)
        k += 1

    df = pd.DataFrame(rows, columns=["date"] + cols)
    return df

df = parse_monthly_vw("6_Portfolios_2x3.csv")

# Identify columns: SMALL LoBM, SMALL HiBM, BIG LoBM, BIG HiBM
def find_col(df, *keys):
    for c in df.columns:
        cu = c.upper().replace(" ", "")
        if all(k.upper().replace(" ", "") in cu for k in keys):
            return c
    raise KeyError(keys)

sl = find_col(df, "SMALL", "LoBM")
sh = find_col(df, "SMALL", "HiBM")
bl = find_col(df, "BIG", "LoBM")
bh = find_col(df, "BIG", "HiBM")

sub = df[["date", sl, sh, bl, bh]].copy()
for c in [sl, sh, bl, bh]:
    sub.loc[sub[c] <= -99.0, c] = np.nan

hml = 0.5 * (sub[sh] + sub[bh]) - 0.5 * (sub[sl] + sub[bl])

out = pd.DataFrame({"date": sub["date"].astype(int), "value": hml.round(4)})
out = out.dropna(subset=["value"]).drop_duplicates(subset=["date"]).sort_values("date")
out.to_csv("output.csv", index=False)
