import re
import numpy as np
import pandas as pd

INPUT = "6_Portfolios_ME_INV_2x3.csv"
OUTPUT = "output.csv"


def is_missing(x):
    return x is None or np.isnan(x) or x in (-99.99, -999.0)


def parse_value_weighted_monthly(path):
    with open(path, encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the value-weighted monthly section header
    start = None
    for i, l in enumerate(lines):
        low = l.lower()
        if "value weighted" in low and "monthly" in low:
            start = i
            break
    if start is None:
        start = -1  # fall back: first data block in file

    # Find column header line (first non-empty line with commas and no leading date)
    header_idx = None
    for j in range(start + 1, len(lines)):
        s = lines[j].strip()
        if not s:
            continue
        first = s.split(",")[0].strip()
        if re.fullmatch(r"\d{6}", first):
            break  # reached data without a header line
        if "," in s:
            header_idx = j
            break

    if header_idx is None:
        raise RuntimeError("Could not find header for value-weighted monthly table")

    header = [h.strip() for h in lines[header_idx].split(",")]
    col_names = header[1:]

    # Data rows
    rows = []
    started = False
    for j in range(header_idx + 1, len(lines)):
        s = lines[j].strip()
        if not s:
            if started:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if re.fullmatch(r"\d{6}", parts[0]):
            started = True
            vals = []
            for p in parts[1:]:
                try:
                    v = float(p)
                except ValueError:
                    v = np.nan
                if is_missing(v):
                    v = np.nan
                vals.append(v)
            rows.append((int(parts[0]), vals))
        else:
            if started:
                break

    ncol = len(col_names)
    data = pd.DataFrame(
        [r[1][:ncol] + [np.nan] * (ncol - len(r[1])) for r in rows],
        index=[r[0] for r in rows],
        columns=col_names,
    )
    data.index.name = "date"
    return data


def find_cols(col_names):
    """Identify SMALL/BIG x LoINV/HiINV columns by name; fall back to positions."""
    norm = {c: c.upper().replace(" ", "") for c in col_names}
    sel = {}
    for c, n in norm.items():
        if "LOINV" in n and n.startswith("SMALL"):
            sel["SL"] = c
        elif "HIINV" in n and n.startswith("SMALL"):
            sel["SH"] = c
        elif "LOINV" in n and n.startswith("BIG"):
            sel["BL"] = c
        elif "HIINV" in n and n.startswith("BIG"):
            sel["BH"] = c
    if len(sel) == 4:
        return sel
    # Positional fallback: 6_Portfolios layout (SMALL Lo, ME1, SMALL Hi, BIG Lo, ME2, BIG Hi)
    return {"SL": col_names[0], "SH": col_names[2], "BL": col_names[3], "BH": col_names[5]}


def main():
    data = parse_value_weighted_monthly(INPUT)
    cols = find_cols(list(data.columns))

    sl = data[cols["SL"]]
    sh = data[cols["SH"]]
    bl = data[cols["BL"]]
    bh = data[cols["BH"]]

    # CMA = 0.5*(Small Lo + Big Lo) - 0.5*(Small Hi + Big Hi)
    cma = 0.5 * (sl + bl) - 0.5 * (sh + bh)

    out = pd.DataFrame({"date": cma.index.astype(int), "value": cma.values})
    out = out.dropna(subset=["value"])
    out = out.sort_values("date").reset_index(drop=True)
    out["date"] = out["date"].astype(int)
    out.to_csv(OUTPUT, index=False)


if __name__ == "__main__":
    main()
