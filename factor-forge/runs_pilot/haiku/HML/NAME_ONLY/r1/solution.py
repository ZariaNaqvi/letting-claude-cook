import re
import numpy as np
import pandas as pd


def main():
    fname = "6_Portfolios_2x3.csv"
    with open(fname, encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the monthly value-weighted block
    start = None
    for i, line in enumerate(lines):
        if "average value weighted returns" in line.lower() and "monthly" in line.lower():
            start = i
            break
    if start is None:
        # fallback: first line that begins with a YYYYMM date
        for i, line in enumerate(lines):
            if re.match(r"^\s*\d{6}\s*,", line):
                start = i - 1
                break
    if start is None:
        raise SystemExit("Could not find monthly value-weighted block")

    date_re = re.compile(r"^\d{6}$")
    rows = []
    started = False
    for line in lines[start + 1:]:
        s = line.strip()
        if not s:
            if started:
                break
            continue
        parts = [p.strip() for p in s.split(",")]
        if date_re.match(parts[0]) and len(parts) >= 7:
            started = True
            vals = []
            for p in parts[1:7]:
                try:
                    v = float(p)
                except ValueError:
                    v = np.nan
                if v != v or v == -99.99 or v == -999.0:
                    v = np.nan
                vals.append(v)
            rows.append((int(parts[0]), vals))
        else:
            if started:
                break

    # Column order in file: SMALL LoBM, ME1 BM2, SMALL HiBM, BIG LoBM, ME2 BM2, BIG HiBM
    df = pd.DataFrame(
        [r[1] for r in rows],
        index=[r[0] for r in rows],
        columns=["SL", "SM", "SH", "BL", "BM", "BH"],
    )
    df.index.name = "date"

    hml = 0.5 * (df["SH"] + df["BH"]) - 0.5 * (df["SL"] + df["BL"])
    out = pd.DataFrame({"date": df.index.astype(int), "value": hml.values})
    out = out.dropna(subset=["value"])
    out["date"] = out["date"].astype(int)
    out.to_csv("output.csv", index=False, columns=["date", "value"])


if __name__ == "__main__":
    main()
