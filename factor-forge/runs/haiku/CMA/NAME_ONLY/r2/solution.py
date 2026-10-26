import re
import numpy as np
import pandas as pd

FILE = "6_Portfolios_ME_INV_2x3.csv"
OUT = "output.csv"


def is_missing(x):
    return x is None or np.isnan(x) or np.isclose(x, -99.99) or np.isclose(x, -999.0)


def parse_vw_monthly(path):
    with open(path, encoding="latin-1") as f:
        lines = f.read().splitlines()

    # locate the value-weighted monthly block
    start = None
    for i, line in enumerate(lines):
        low = line.lower()
        if "value weighted" in low and "monthly" in low:
            start = i
            break
    if start is None:
        raise RuntimeError("Value-weighted monthly block not found")

    # header line: starts with a comma and holds portfolio names
    header = None
    data_start = None
    for j in range(start + 1, len(lines)):
        s = lines[j].strip()
        if header is None and s.startswith(","):
            header = [c.strip() for c in s.split(",")]
            data_start = j + 1
            break
    if header is None:
        raise RuntimeError("Header line not found")

    rows = []
    started = False
    for j in range(data_start, len(lines)):
        s = lines[j].strip()
        m = re.match(r"^(\d{6})\s*,", s)
        if m:
            started = True
            parts = [p.strip() for p in s.split(",")]
            date = int(parts[0])
            vals = []
            for p in parts[1:]:
                try:
                    v = float(p)
                except ValueError:
                    v = np.nan
                if is_missing(v):
                    v = np.nan
                vals.append(v)
            rows.append((date, vals))
        else:
            if started:
                break  # end of monthly block

    ncols = len(header) - 1  # header[0] is empty label column
    df = pd.DataFrame(
        [r[1][:ncols] + [np.nan] * max(0, ncols - len(r[1])) for r in rows],
        index=[r[0] for r in rows],
        columns=header[1:],
    )
    df.index.name = "date"
    return df


def find_col(df, target_words):
    norm = {re.sub(r"\s+", " ", c).strip().upper(): c for c in df.columns}
    key = " ".join(target_words).upper()
    if key in norm:
        return norm[key]
    return None


def main():
    df = parse_vw_monthly(FILE)

    cols = {
        "SL": find_col(df, ["SMALL", "LoINV"]),
        "SH": find_col(df, ["SMALL", "HiINV"]),
        "BL": find_col(df, ["BIG", "LoINV"]),
        "BH": find_col(df, ["BIG", "HiINV"]),
    }
    if any(v is None for v in cols.values()):
        # fallback to positional layout:
        # SMALL LoINV, ME1 INV2, SMALL HiINV, BIG LoINV, ME2 INV2, BIG HiINV
        allc = list(df.columns)
        cols = {"SL": allc[0], "SH": allc[2], "BL": allc[3], "BH": allc[5]}

    sl = df[cols["SL"]].astype(float)
    sh = df[cols["SH"]].astype(float)
    bl = df[cols["BL"]].astype(float)
    bh = df[cols["BH"]].astype(float)

    cma = 0.5 * (sl + bl) - 0.5 * (sh + bh)

    out = pd.DataFrame({
        "date": [int(d) for d in df.index],
        "value": cma.values,
    })
    out = out.dropna(subset=["value"])
    out = out.sort_values("date").reset_index(drop=True)
    out["date"] = out["date"].astype(int)
    out.to_csv(OUT, index=False, columns=["date", "value"])


if __name__ == "__main__":
    main()
