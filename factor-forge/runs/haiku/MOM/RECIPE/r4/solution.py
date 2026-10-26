import re
import numpy as np
import pandas as pd

FILE = "6_Portfolios_ME_Prior_12_2.csv"
MISSING = {-99.99, -999.0}


def parse_first_vw_monthly(path):
    with open(path, encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the first value-weighted monthly block
    start = None
    for i, line in enumerate(lines):
        if "Average Value Weighted Returns -- Monthly" in line:
            start = i
            break
    if start is None:
        start = 0  # fallback: search from top

    # Locate the header line containing the portfolio names
    header_idx = None
    for j in range(start, len(lines)):
        if "SMALL LoPRIOR" in lines[j] and "," in lines[j]:
            header_idx = j
            break
    if header_idx is None:
        raise RuntimeError("Header not found")

    header = [h.strip() for h in lines[header_idx].split(",")]
    col_index = {name: k for k, name in enumerate(header) if name}

    rows = []
    started = False
    for line in lines[header_idx + 1:]:
        parts = [p.strip() for p in line.split(",")]
        if parts and re.fullmatch(r"\d{6}", parts[0] or ""):
            started = True
            vals = []
            for p in parts[1:len(header)]:
                try:
                    v = float(p)
                except ValueError:
                    v = np.nan
                if v != v or any(abs(v - m) < 1e-9 for m in MISSING):
                    v = np.nan
                vals.append(v)
            while len(vals) < len(header) - 1:
                vals.append(np.nan)
            rows.append([int(parts[0])] + vals)
        else:
            if started:
                break  # end of first table

    cols = ["date"] + [header[k] for k in range(1, len(header)) if header[k]]
    # Build frame aligned to header positions (index 0 is the date column)
    data = []
    for r in rows:
        rec = {"date": r[0]}
        for name, k in col_index.items():
            if k == 0:
                continue
            rec[name] = r[k]
        data.append(rec)
    df = pd.DataFrame(data)
    return df


def main():
    df = parse_first_vw_monthly(FILE)

    needed = ["SMALL HiPRIOR", "BIG HiPRIOR", "SMALL LoPRIOR", "BIG LoPRIOR"]
    df = df.dropna(subset=needed).copy()

    df["value"] = (
        0.5 * (df["SMALL HiPRIOR"] + df["BIG HiPRIOR"])
        - 0.5 * (df["SMALL LoPRIOR"] + df["BIG LoPRIOR"])
    )

    out = pd.DataFrame({
        "date": df["date"].astype(int),
        "value": df["value"].astype(float),
    }).sort_values("date").reset_index(drop=True)

    out.to_csv("output.csv", index=False)


if __name__ == "__main__":
    main()
