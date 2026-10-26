import re
import math
import pandas as pd


def main():
    fname = "6_Portfolios_ME_INV_2x3.csv"
    with open(fname, encoding="latin-1") as f:
        lines = f.read().splitlines()

    # Locate the first "Average Value Weighted Returns -- Monthly" block
    title_idx = None
    for i, line in enumerate(lines):
        if "average value weighted returns" in line.lower() and "monthly" in line.lower():
            title_idx = i
            break
    if title_idx is None:
        raise RuntimeError("Value-weighted monthly block not found")

    # Header line: first non-empty line after the title
    j = title_idx + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    header = [" ".join(c.split()) for c in lines[j].split(",")]

    def col_index(name):
        for k, h in enumerate(header):
            if h.upper() == name.upper():
                return k
        raise RuntimeError(f"Column not found: {name}")

    i_sl = col_index("SMALL LoINV")
    i_bl = col_index("BIG LoINV")
    i_sh = col_index("SMALL HiINV")
    i_bh = col_index("BIG HiINV")
    ncols = len(header)

    missing_vals = (-99.99, -999.0)

    rows = []
    started = False
    for line in lines[j + 1:]:
        s = line.strip()
        if not s:
            if started:
                break  # end of first block
            continue
        parts = [p.strip() for p in s.split(",")]
        if not re.fullmatch(r"\d{6}", parts[0]):
            if started:
                break  # reached next block / text
            continue
        started = True
        if len(parts) < ncols:
            continue
        try:
            vals = {
                "sl": float(parts[i_sl]),
                "bl": float(parts[i_bl]),
                "sh": float(parts[i_sh]),
                "bh": float(parts[i_bh]),
            }
        except ValueError:
            continue
        if any(math.isnan(v) or any(abs(v - m) < 1e-9 for m in missing_vals)
               for v in vals.values()):
            continue
        cma = 0.5 * (vals["sl"] + vals["bl"]) - 0.5 * (vals["sh"] + vals["bh"])
        rows.append((int(parts[0]), cma))

    out = pd.DataFrame(rows, columns=["date", "value"])
    out["date"] = out["date"].astype(int)
    out.to_csv("output.csv", index=False)


if __name__ == "__main__":
    main()
