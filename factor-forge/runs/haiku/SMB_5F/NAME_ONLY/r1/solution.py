import math
import pandas as pd


def parse_vw_monthly(fname):
    """Parse the first (Average Value Weighted Returns -- Monthly) block.
    Returns dict: YYYYMM -> list of 6 floats (NaN for missing)."""
    rows = {}
    in_block = False
    with open(fname, encoding="latin-1") as f:
        for line in f:
            s = line.strip()
            if not in_block:
                if "Average Value Weighted Returns -- Monthly" in s:
                    in_block = True
                continue
            if s.startswith("Average") or s.startswith("Annual"):
                break
            if s == "":
                if rows:
                    break
                continue
            parts = [p.strip() for p in s.split(",")]
            first = parts[0]
            if len(first) == 6 and first.isdigit():
                vals = []
                for p in parts[1:7]:
                    try:
                        v = float(p)
                    except ValueError:
                        v = math.nan
                    if v <= -99.0:  # -99.99 / -999 missing codes
                        v = math.nan
                    vals.append(v)
                if len(vals) == 6:
                    rows[int(first)] = vals
    return rows


def smb_component(rows):
    """Per month: mean(small 3) - mean(big 3). Columns order:
    small Lo, small Mid, small Hi, big Lo, big Mid, big Hi."""
    out = {}
    for d, v in rows.items():
        if any(math.isnan(x) for x in v):
            continue
        small = (v[0] + v[1] + v[2]) / 3.0
        big = (v[3] + v[4] + v[5]) / 3.0
        out[d] = small - big
    return out


def main():
    bm = parse_vw_monthly("6_Portfolios_2x3.csv")
    op = parse_vw_monthly("6_Portfolios_ME_OP_2x3.csv")
    inv = parse_vw_monthly("6_Portfolios_ME_INV_2x3.csv")

    s_bm = smb_component(bm)
    s_op = smb_component(op)
    s_inv = smb_component(inv)

    common = sorted(set(s_bm) & set(s_op) & set(s_inv))

    records = []
    for d in common:
        val = (s_bm[d] + s_op[d] + s_inv[d]) / 3.0
        records.append((int(d), val))

    out = pd.DataFrame(records, columns=["date", "value"])
    out["date"] = out["date"].astype(int)
    out.to_csv("output.csv", index=False)


if __name__ == "__main__":
    main()
