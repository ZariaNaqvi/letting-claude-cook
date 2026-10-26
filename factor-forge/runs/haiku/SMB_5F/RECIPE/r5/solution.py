import re
import pandas as pd

FILES = [
    "6_Portfolios_2x3.csv",
    "6_Portfolios_ME_OP_2x3.csv",
    "6_Portfolios_ME_INV_2x3.csv",
]
MISSING = {-99.99, -999.0}
TITLE_KEY = "Average Value Weighted Returns"


def parse_vw_monthly(path):
    """Parse the FIRST (value-weighted monthly) block of a Ken French 2x3 file."""
    with open(path, encoding="latin-1") as f:
        lines = f.read().splitlines()

    start = None
    for i, line in enumerate(lines):
        if TITLE_KEY in line and "Monthly" in line:
            start = i
            break
    if start is None:
        raise ValueError(f"Value-weighted monthly block not found in {path}")

    header = None
    rows = []
    for line in lines[start + 1:]:
        parts = [p.strip() for p in line.split(",")]
        if header is None:
            if all(p == "" for p in parts):
                continue
            header = parts
            continue
        if not parts or not re.fullmatch(r"\d{6}", parts[0]):
            if rows:
                break  # end of the monthly block
            continue
        rows.append(parts)

    if header is None or not rows:
        raise ValueError(f"No data parsed from {path}")

    ncols = len(header)
    data = []
    for parts in rows:
        date = int(parts[0])
        vals = []
        for j in range(1, ncols):
            try:
                v = float(parts[j]) if j < len(parts) and parts[j] != "" else float("nan")
            except ValueError:
                v = float("nan")
            if v in MISSING:
                v = float("nan")
            vals.append(v)
        data.append([date] + vals)

    cols = ["date"] + [f"c{j}" for j in range(1, ncols)]
    df = pd.DataFrame(data, columns=cols)

    # Identify small / big columns by header names; fall back to position.
    names = header[1:]
    small_idx = [k for k, n in enumerate(names) if "SMALL" in n.upper() or n.upper().startswith("ME1")]
    big_idx = [k for k, n in enumerate(names) if "BIG" in n.upper() or n.upper().startswith("ME2")]
    if len(small_idx) != 3 or len(big_idx) != 3:
        small_idx = [0, 1, 2]
        big_idx = [3, 4, 5]

    small_cols = [f"c{k + 1}" for k in small_idx]
    big_cols = [f"c{k + 1}" for k in big_idx]

    out = pd.DataFrame({"date": df["date"]})
    out["smb"] = df[small_cols].mean(axis=1) - df[big_cols].mean(axis=1)
    return out.set_index("date")["smb"]


def main():
    series = [parse_vw_monthly(fn) for fn in FILES]

    common = series[0].dropna()
    for s in series[1:]:
        common = common.to_frame("a").join(s.dropna().rename("b"), how="inner")
        common = common.mean(axis=1)

    # 'common' is now the average of the three SMB_x series over common months
    # (joined on the intersection of dates); recompute cleanly for clarity:
    frames = [s.dropna() for s in series]
    idx = frames[0].index
    for f in frames[1:]:
        idx = idx.intersection(f.index)
    idx = sorted(idx)

    smb = sum(f.loc[idx] for f in frames) / 3.0
    result = pd.DataFrame({"date": [int(d) for d in idx], "value": smb.values})
    result = result.dropna().sort_values("date").reset_index(drop=True)
    result["date"] = result["date"].astype(int)

    result.to_csv("output.csv", index=False, columns=["date", "value"])


if __name__ == "__main__":
    main()
