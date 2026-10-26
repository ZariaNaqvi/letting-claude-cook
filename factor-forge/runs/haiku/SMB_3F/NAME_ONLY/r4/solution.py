import re
import pandas as pd
import numpy as np

INPUT = "6_Portfolios_2x3.csv"
OUTPUT = "output.csv"
MISSING = {-99.99, -999.0}
DATE_RE = re.compile(r"^\d{6}$")


def main():
    with open(INPUT, encoding="latin-1") as fh:
        lines = fh.read().splitlines()

    # Locate the header of the first "Average Value Weighted Returns -- Monthly" table.
    start = None
    for i, line in enumerate(lines):
        low = line.lower()
        if "value weighted" in low and "monthly" in low:
            start = i
            break
    if start is None:
        # Fallback: first table whose title mentions "value" and "monthly"
        for i, line in enumerate(lines):
            low = line.lower()
            if "value" in low and "monthly" in low:
                start = i
                break
    if start is None:
        raise RuntimeError("Could not locate value-weighted monthly table")

    records = []
    started = False
    for line in lines[start + 1:]:
        s = line.strip()
        fields = [f.strip() for f in s.split(",")]
        if fields and DATE_RE.match(fields[0]):
            started = True
            if len(fields) < 7:
                continue
            vals = []
            for f in fields[1:7]:
                try:
                    v = float(f)
                except ValueError:
                    v = np.nan
                if v in MISSING:
                    v = np.nan
                vals.append(v)
            records.append((int(fields[0]), vals))
        else:
            if started:
                # End of the monthly value-weighted block
                break

    if not records:
        raise RuntimeError("No monthly data rows found")

    out_rows = []
    for date, v in records:
        # Columns: SMALL LoBM, ME1 BM2, SMALL HiBM, BIG LoBM, ME2 BM2, BIG HiBM
        small = np.mean(v[0:3])
        big = np.mean(v[3:6])
        smb = small - big
        if np.isnan(smb):
            continue
        out_rows.append((date, float(smb)))

    df = pd.DataFrame(out_rows, columns=["date", "value"])
    df["date"] = df["date"].astype(int)
    df.to_csv(OUTPUT, index=False)


if __name__ == "__main__":
    main()
