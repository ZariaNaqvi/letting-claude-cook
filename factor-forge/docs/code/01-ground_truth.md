# 01 - `ground_truth.py`

## In one sentence

`ground_truth.py` is the human answer key: it reads Ken French's raw portfolio CSVs, rebuilds all 8 factors by hand-coded formulas, and checks each one against the official factor series French publishes.

## Why it exists

The experiment asks models to rebuild factors from raw files. Before you can grade a model, you need to prove two things:

1. The task is possible. A careful human (this file) can rebuild every factor from the same raw files the model gets.
2. You know how close "correct" can get. Because the inputs and the official series are both rounded, even a perfect rebuild is off by a tiny amount. This file measures that amount (about 0.3 to 0.4 basis points), and `make_tasks.py` uses it to set the pass threshold.

It also writes the two series the rest of the project uses:

- `data/truth/<TASK>.csv` - the official series, copied out of French's factor files. The scorer grades models against this.
- `data/reference/<TASK>.csv` - this file's own rebuild. It is kept for comparison.

## How to run it

From inside `~/letting-claude-cook/factor-forge` with the venv active:

```bash
python -I ground_truth.py
```

The `-I` flag runs Python in "isolated mode": it ignores `PYTHON...` environment variables and your user site-packages, so the result does not depend on anything odd in your shell. It works without `-I` too.

Successful output is one table (real output):

```
         task                                official           recipe  months  first   last  coverage  rmse_bp  max_abs_bp  n_diff_gt_1bp   corr
          HML       F-F_Research_Data_Factors.csv:HML              hml    1202 192607 202608    1.0000   0.2908      0.5000              0 1.0000
       SMB_3F       F-F_Research_Data_Factors.csv:SMB           smb_3f    1202 192607 202608    1.0000   0.2964      0.5000              0 1.0000
       SMB_5F F-F_Research_Data_5_Factors_2x3.csv:SMB           smb_5f     758 196307 202608    1.0000   0.2824      0.4989              0 1.0000
          RMW F-F_Research_Data_5_Factors_2x3.csv:RMW              rmw     758 196307 202608    1.0000   0.2912      0.5000              0 1.0000
          CMA F-F_Research_Data_5_Factors_2x3.csv:CMA              cma     758 196307 202608    1.0000   0.2888      0.5000              0 1.0000
          MOM             F-F_Momentum_Factor.csv:Mom              mom    1196 192701 202608    1.0000   0.4071      1.0000              0 1.0000
       ST_REV       F-F_ST_Reversal_Factor.csv:ST_Rev           st_rev    1207 192602 202608    1.0000   0.4083      1.0000              0 1.0000
       LT_REV       F-F_LT_Reversal_Factor.csv:LT_Rev           lt_rev    1148 193101 202608    1.0000   0.4182      1.0000              0 1.0000
HML_5F(check) F-F_Research_Data_5_Factors_2x3.csv:HML              hml     758 196307 202608    1.0000   0.2893      0.5000              0 1.0000
 SMB_3F~9port       F-F_Research_Data_Factors.csv:SMB smb_3f_alt_9port     758 196307 202608    0.6306  60.2547    350.6889            737 0.9801
 SMB_5F~3port F-F_Research_Data_5_Factors_2x3.csv:SMB smb_5f_alt_3port     758 196307 202608    1.0000  60.2530    350.6600            735 0.9801
```

How to read it: the first 8 rows are the real tasks. All have coverage 1.0 (every official month rebuilt), RMSE under half a basis point, and correlation that rounds to 1.0000. The last two rows are deliberately wrong recipes. Their RMSE is about 60 bp, so they clearly fail. That shows the 1 bp threshold can tell a right recipe from a near-miss.

Running it overwrites `data/truth/`, `data/reference/` and `data/ground_truth_results.csv`. With the same raw files it writes the same numbers again.

There is also a helper mode that just lists the tables inside each raw file:

```bash
python -I ground_truth.py --blocks
```

Real output (first few lines):

```
## 6_Portfolios_2x3.csv
  [0] header L16, rows L17-1218 monthly 192607-202608 n=1202 ncol=6 :: Average Value Weighted Returns -- Monthly
  [1] header L1222, rows L1223-2424 monthly 192607-202608 n=1202 ncol=6 :: Average Equal Weighted Returns -- Monthly
  [2] header L2428, rows L2429-2527 annual 1927-2025 n=99 ncol=6 :: Average Value Weighted Returns -- Annual
  [3] header L2531, rows L2532-2630 annual 1927-2025 n=99 ncol=6 :: Average Equal Weighted Returns -- Annual
  [4] header L2634, rows L2635-3836 monthly 192607-202608 n=1202 ncol=6 :: Number of Firms in Portfolios
  [5] header L3840, rows L3841-5042 monthly 192607-202608 n=1202 ncol=6 :: Average Market Cap
  ...
```

This is why the task is hard: one file holds about ten stacked tables, and only block 0 is the right one.

## What a raw file looks like

Here are the first lines of `data/raw/6_Portfolios_2x3.csv` (real excerpt):

```
This file was created using the 202608 CRSP database.
It contains value- and equal-weighted returns for portfolios formed on ME and BEME.

The portfolios are constructed at the end of June.  BEME is book value at the last fiscal year end of the prior calendar year
divided by ME at the end of December of the prior year.
Annual returns are from January to December.

Missing data are indicated by -99.99 or -999.

The break points include utilities and include financials

The  portfolios  include utilities and include financials.


  Average Value Weighted Returns -- Monthly
,SMALL LoBM,ME1 BM2,SMALL HiBM,BIG LoBM,ME2 BM2,BIG HiBM
192607,   1.0866,   0.9068,  -0.1275,   5.7178,   1.9709,   1.4225
192608,   0.7831,   1.1829,   5.4422,   2.7268,   2.6766,   6.3196
192609,  -2.8045,  -0.0518,  -0.4399,   1.4777,   0.0850,  -0.7906
```

Things to notice:

- A text preamble comes first.
- Then a title line (`Average Value Weighted Returns -- Monthly`).
- Then a header line that starts with a comma (the first column, the date, has no name).
- Then data rows. The first field is a date like `192607` (July 1926). Values are monthly returns in percent, so `1.0866` means 1.0866%.
- The six columns are a 2 x 3 sort. ME is market equity (size): SMALL / ME1 is small, BIG / ME2 is big. BM is book-to-market: Lo is growth, `BM2` is neutral (middle), Hi is value. So `SMALL HiBM` is "small value stocks" and `BIG LoBM` is "big growth stocks".
- "Value weighted" means each stock counts in proportion to its market cap, so a portfolio return is what you would earn holding the stocks in market proportions.

The official factor file looks similar but simpler. The top of `F-F_Research_Data_Factors.csv`:

```
,Mkt-RF,SMB,HML,RF
192607,   2.89,  -2.42,  -2.75,   0.22
192608,   2.64,  -1.44,   4.13,   0.25
```

Note the official factors have only 2 decimal places. The portfolio returns above have 4.

## Walkthrough

### Imports and constants

```python
HERE = os.path.dirname(os.path.abspath(__file__))
MISSING_CODES = (-99.99, -999.0)
```

`HERE` is the folder this file lives in. Using it means the default paths work no matter which folder you run the command from. `MISSING_CODES` are the numbers French uses to mean "no data" (the file preamble says so: "Missing data are indicated by -99.99 or -999").

### The date-row pattern (a regex)

```python
DATA_ROW = re.compile(r"^\s*(\d{4}|\d{6})\s*,")  # YYYY (annual) or YYYYMM (monthly)
```

A **regular expression** (regex) is a small pattern language for matching text. `re.compile` turns the pattern into an object you can reuse. Piece by piece:

- `^` - start of the line.
- `\s*` - any amount of whitespace (including none).
- `(\d{4}|\d{6})` - exactly 4 digits (a year, like `1927`) OR exactly 6 digits (a month, like `192607`).
- `\s*,` - optional spaces, then a comma.

So `DATA_ROW.match(line)` is true for data rows and false for titles, headers and blank lines. The `r"..."` prefix makes it a "raw string" so the backslashes reach the regex unchanged.

### `list_blocks(path)` - find every table in a file

```python
    with open(path, "rb") as fh:
        text = fh.read().decode("latin-1")
    lines = [ln.replace("\r", "") for ln in text.split("\n")]
```

The file is opened in binary mode (`"rb"`) and decoded by hand. The comment above this code explains why: French's files use Windows line endings (`\r\n`), but some also contain stray lone `\r` characters in the middle of a line. Python's normal text mode would treat a lone `\r` as a line break and split a header in two. So the code splits on `\n` only and deletes every `\r`. `latin-1` is a text encoding that can decode any byte, so reading never fails on an odd character.

```python
        if line.startswith(","):  # header row of a table
            header = [c.strip() for c in line.split(",")[1:]]
```

A line that starts with a comma is a table header. `line.split(",")` breaks it into fields; `[1:]` drops the empty first field (the unnamed date column); `.strip()` removes spaces. This is a **list comprehension**: `[expression for item in list]` builds a new list in one line.

```python
            title_parts, j = [], i - 1
            while j >= 0 and lines[j].strip() and not DATA_ROW.match(lines[j]):
                title_parts.insert(0, lines[j].strip())
                j -= 1
```

To find the table's title, it walks backward from the header and collects lines until it hits a blank line or a data row. That collects `Average Value Weighted Returns -- Monthly` for block 0.

```python
            while k < len(lines) and DATA_ROW.match(lines[k]):
                rows.append(k)
                k += 1
```

Then it walks forward and records the line numbers of every data row until the first non-data line. That is the end of the table.

```python
                blocks.append(dict(
                    index=len(blocks), title=title, header=header,
                    header_line=i + 1, first_line=rows[0] + 1, last_line=rows[-1] + 1,
                    n_rows=len(rows), freq="monthly" if len(first_date) == 6 else "annual",
```

Each table becomes a dictionary describing it: its number, title, column names, where it starts and ends (1-based line numbers, as a text editor shows them), how many rows, and whether it is monthly (6-digit dates) or annual (4-digit dates). It also keeps `_rows` (the row line numbers) and later `_lines` (all lines of the file) so the next function can read the values.

### `read_french_block(path, block_index_or_title=0)` - one table as a DataFrame

```python
    if isinstance(block_index_or_title, int):
        b = blocks[block_index_or_title]
    else:
        matches = [b for b in blocks if block_index_or_title.lower() in b["title"].lower()]
```

You can ask for a table by number (`0`) or by part of its title (`"Value Weighted Returns -- Monthly"`). Title matching is case-insensitive (`.lower()` on both sides) and takes the first match. If nothing matches, it raises a `KeyError` with a clear message. If the block is annual, it raises a `ValueError`, because every factor here is monthly.

```python
    for r in b["_rows"]:
        parts = [p.strip() for p in b["_lines"][r].split(",")]
        dates.append(int(parts[0]))
        recs.append([float(x) for x in parts[1:1 + ncol]])
    df = pd.DataFrame(recs, index=pd.Index(dates, name="date"), columns=b["header"])
```

For each data row it splits on commas, turns the date into an integer (`192607`) and the rest into floats. `parts[1:1 + ncol]` keeps only as many values as the header has columns. The docstring notes that some rows have extra fields, but only in blocks that are never used here.

A **pandas DataFrame** is a table with labeled rows (the "index") and labeled columns. Here the index is the date and the columns are the six portfolio names.

```python
    for code in MISSING_CODES:
        df = df.mask(np.isclose(df, code))
```

`np.isclose` checks "is this number equal to -99.99 (allowing for float rounding)?" for every cell. `df.mask(condition)` replaces cells where the condition is true with `NaN` ("not a number", pandas' marker for missing). This stops a missing-data code from being treated as a -99.99% return.

### Factor recipes

```python
VW = "Value Weighted Returns -- Monthly"


def _p(raw, fname):
    return read_french_block(os.path.join(raw, fname), VW)
```

`_p` is a shortcut: "read the value-weighted monthly table of this file." Every recipe uses it. The leading underscore is a Python convention meaning "internal helper". (`score.py` later swaps `VW` to the equal-weighted title to build a "wrong table" version of each factor. See doc 06.)

```python
def _hi_minus_lo(df, s_hi, b_hi, s_lo, b_lo):
    return 0.5 * (df[s_hi] + df[b_hi]) - 0.5 * (df[s_lo] + df[b_lo])
```

This one line is the heart of six of the eight factors. It takes four column names and returns, for every month:

average of (small long leg, big long leg) minus average of (small short leg, big short leg).

Because `df[s_hi]` is a whole column (a pandas Series), the arithmetic happens for all ~1,200 months at once. You do not need a loop.

Why average a small and a big portfolio? It makes the factor roughly **size-neutral**. Small stocks behave differently from big ones. If you just compared all value stocks with all growth stocks, a size effect could leak in. Taking the small spread and the big spread and averaging them gives each size group equal say.

```python
def _smb3(df):
    """Average of the 3 small portfolios minus average of the 3 big portfolios."""
    small = [c for c in df.columns if c.startswith("SMALL") or c.startswith("ME1")]
    big = [c for c in df.columns if c.startswith("BIG") or c.startswith("ME2")]
    assert len(small) == 3 and len(big) == 3, df.columns
    return df[small].mean(axis=1) - df[big].mean(axis=1)
```

SMB ("small minus big") uses all six portfolios. It picks the three small columns by name (`SMALL...` or `ME1...`) and the three big ones (`BIG...` or `ME2...`). `assert` stops the program with an error if it did not find exactly 3 and 3, which would mean the column names were not what we expected. `.mean(axis=1)` averages across columns (one average per month). `axis=0` would average down the rows instead.

### The eight factors

```python
def hml(raw):
    # HML = 1/2 (Small Value + Big Value) - 1/2 (Small Growth + Big Growth)
    d = _p(raw, "6_Portfolios_2x3.csv")
    return _hi_minus_lo(d, "SMALL HiBM", "BIG HiBM", "SMALL LoBM", "BIG LoBM")
```

**HML (high minus low)** is the value factor. High book-to-market stocks ("value": cheap relative to their accounting book value) minus low book-to-market stocks ("growth": expensive relative to book). Economically, ½(Small Value + Big Value) − ½(Small Growth + Big Growth) is the monthly return of a portfolio that is long value and short growth, with the same weight in small and big stocks. If HML is positive in a month, value beat growth that month. Fama and French argue its long-run average is positive (the value premium).

```python
def smb_3f(raw):
    # SMB (3-factor) = 1/3 (SV + SN + SG) - 1/3 (BV + BN + BG), size x B/M sort
    return _smb3(_p(raw, "6_Portfolios_2x3.csv"))
```

**SMB (3-factor version)** is the size factor: average return of the three small portfolios minus the three big ones. Averaging across value, neutral and growth makes it roughly neutral to value.

```python
def smb_5f(raw):
    a = _smb3(_p(raw, "6_Portfolios_2x3.csv"))
    b = _smb3(_p(raw, "6_Portfolios_ME_OP_2x3.csv"))
    c = _smb3(_p(raw, "6_Portfolios_ME_INV_2x3.csv"))
    return (a + b + c) / 3.0
```

**SMB (5-factor version)** is different. In the 5-factor model, French computes a small-minus-big spread inside three different 2 x 3 sorts (size x book-to-market, size x profitability, size x investment) and averages the three. That is the same as averaging 9 small portfolios minus 9 big ones. The profitability and investment files start in July 1963, so this series starts in 196307. When you add two pandas Series, pandas lines them up by date first. A month missing from any of the three gives `NaN`.

```python
def rmw(raw):
    # RMW = 1/2 (Small Robust + Big Robust) - 1/2 (Small Weak + Big Weak)
    d = _p(raw, "6_Portfolios_ME_OP_2x3.csv")
    return _hi_minus_lo(d, "SMALL HiOP", "BIG HiOP", "SMALL LoOP", "BIG LoOP")
```

**RMW (robust minus weak)** is the profitability factor. OP is operating profitability. Long firms with high profitability, short firms with low profitability.

```python
def cma(raw):
    # CMA = 1/2 (Small Conservative + Big Conservative) - 1/2 (Small Aggressive + Big Aggressive)
    d = _p(raw, "6_Portfolios_ME_INV_2x3.csv")
    return _hi_minus_lo(d, "SMALL LoINV", "BIG LoINV", "SMALL HiINV", "BIG HiINV")
```

**CMA (conservative minus aggressive)** is the investment factor. INV is asset growth. "Conservative" firms invest little (Lo INV), "aggressive" firms invest a lot (Hi INV). Note the order: the long leg is **Lo**INV. The finding is that low-investment firms earn higher average returns, so the factor is defined to be long them.

```python
def mom(raw):
    # Mom = 1/2 (Small High + Big High) - 1/2 (Small Low + Big Low), prior (-12,-2)
    d = _p(raw, "6_Portfolios_ME_Prior_12_2.csv")
    return _hi_minus_lo(d, "SMALL HiPRIOR", "BIG HiPRIOR", "SMALL LoPRIOR", "BIG LoPRIOR")
```

**MOM (momentum)**. Stocks are sorted by their return from 12 months ago to 2 months ago ("prior 12-2"). Long past winners (Hi PRIOR), short past losers (Lo PRIOR). The most recent month is skipped on purpose because of the short-term reversal effect below. Momentum says recent winners tend to keep winning for a while.

```python
def st_rev(raw):
    # ST_Rev = 1/2 (Small Low + Big Low) - 1/2 (Small High + Big High), prior (-1,-1)
    d = _p(raw, "6_Portfolios_ME_Prior_1_0.csv")
    return _hi_minus_lo(d, "SMALL LoPRIOR", "BIG LoPRIOR", "SMALL HiPRIOR", "BIG HiPRIOR")
```

**ST_REV (short-term reversal)**. Sorted on last month's return only. This time the factor is **Low minus High**: long last month's losers, short last month's winners. Why the flipped sign? The effect being captured is that last month's losers tend to bounce back and last month's winners tend to give some back (often explained by liquidity and short-term overreaction). French defines the factor as the strategy that profits from that pattern, so the long leg is the losers. Getting this sign backwards is a classic mistake, and the scorer has a special tag for it (SIGN_FLIP).

```python
def lt_rev(raw):
    # LT_Rev = 1/2 (Small Low + Big Low) - 1/2 (Small High + Big High), prior (-60,-13)
    d = _p(raw, "6_Portfolios_ME_Prior_60_13.csv")
    return _hi_minus_lo(d, "SMALL LoPRIOR", "BIG LoPRIOR", "SMALL HiPRIOR", "BIG HiPRIOR")
```

**LT_REV (long-term reversal)**. Sorted on the return from 5 years ago to 13 months ago. Again **Low minus High**: long long-run losers, short long-run winners. The idea (De Bondt and Thaler) is that investors overreact over several years, and the losers recover. It needs 60 months of history, which is why this series starts later (193101).

### Deliberately wrong recipes

```python
def smb_3f_alt_9port(raw):
    return smb_5f(raw)


def smb_5f_alt_3port(raw):
    return smb_3f(raw)
```

These swap the two SMB definitions. They exist only to show that the two SMBs really differ: the output table shows each swapped version is about 60 bp off. So a model that uses the wrong SMB recipe will fail, not slip through.

### The task table

```python
TASKS = {
    "HML":      (hml,     "F-F_Research_Data_Factors.csv",       "HML"),
    ...
    "LT_REV":   (lt_rev,  "F-F_LT_Reversal_Factor.csv",          "LT_Rev"),
}
```

A dictionary from task id to a tuple of: the recipe function, the official file, and the column in that file. Functions are values in Python, so you can store `hml` in a tuple and call it later with `fn(raw)`.

`ALT_TESTS` has three extra checks: HML from the 5-factor file (to confirm it equals the 3-factor HML, which is why `HML_5F` was dropped as a task), and the two swapped SMB recipes.

### `official(raw, fname, col)`

```python
def official(raw, fname, col):
    # Official factor files: block 0 is the monthly table (its title is the file preamble)
    return read_french_block(os.path.join(raw, fname), 0)[col]
```

Reads block 0 of an official factor file and returns one column, for example `HML`. These official files are never given to the models.

### `compare(off, ref)` - how close is the rebuild?

```python
    j = pd.concat([off.rename("off"), ref.rename("ref")], axis=1).dropna()
    err = j["ref"] - j["off"]
```

`pd.concat(..., axis=1)` puts the two series side by side as columns, lined up by date. `.dropna()` keeps only months where both have a value. `err` is the monthly difference.

```python
        coverage=len(j) / off.notna().sum(),
        rmse_bp=float(np.sqrt((err ** 2).mean()) * 100),
        max_abs_bp=float(err.abs().max() * 100),
        n_diff_gt_1bp=int((err.abs() > 0.0100001).sum()),
        corr=float(j["ref"].corr(j["off"])),
```

- **coverage**: matched months divided by official months. 1.0 means every month was rebuilt.
- **rmse_bp**: root mean squared error. Square each error, average, take the square root. Values are in percent, and 1 basis point (bp) = 0.01 percent, so multiplying by 100 converts percent to bp.
- **max_abs_bp**: the single worst month, in bp.
- **n_diff_gt_1bp**: how many months are off by more than 1 bp. The `0.0100001` is a hair above 0.01 so floating-point noise does not count a 1.0 bp rounding gap.
- **corr**: Pearson correlation between the two series.

Why is the human RMSE about 0.29 bp and not 0? The official factors are rounded to 2 decimals (0.01% = 1 bp). Rounding error is spread evenly between -0.5 and +0.5 bp, and the RMS of an even spread of width 1 is 1/sqrt(12), about 0.29. That is exactly what you see for the 2x3 tasks. The momentum and reversal input files are themselves rounded to 2 decimals, which adds a second rounding and pushes RMSE to about 0.41 and the max error to 1.0 bp.

### `main()` - command line and output files

```python
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=os.path.join(HERE, "data", "raw"))
    ap.add_argument("--out", default=os.path.join(HERE, "data"))
    ap.add_argument("--blocks", action="store_true", help="just list table blocks per file")
    a = ap.parse_args()
```

**argparse** is Python's standard library for command-line options. Each `add_argument` declares a flag. `default=` is used if you do not type it. `action="store_true"` makes a flag that takes no value: it is `False` unless you type `--blocks`. `a.raw`, `a.out` and `a.blocks` then hold the values.

If `--blocks` is set, it prints the table list shown above and stops (`return 0`).

```python
    for tid, (fn, f, col) in list(TASKS.items()) + list(ALT_TESTS.items()):
        off = official(a.raw, f, col)
        ref = fn(a.raw)
        r = dict(task=tid, official=f"{f}:{col}", recipe=fn.__name__, **compare(off, ref))
```

For every task and extra check: load the official series, compute the rebuild, compare. `**compare(...)` unpacks the dictionary of metrics into the new dictionary. `fn.__name__` is the function's name as text (`"hml"`).

```python
        if tid in TASKS:
            pd.DataFrame({"date": off.index, "value": off.values}).to_csv(
                os.path.join(a.out, "truth", f"{tid}.csv"), index=False)
            ref_al = ref.reindex(off.index)  # same months as official
```

Only the 8 real tasks get files. The official series goes to `truth/`. The rebuild is `reindex`ed to exactly the official months (adding NaN where missing, dropping extras), rounded to 4 decimals, and saved to `reference/`. Both files have two columns, `date,value`, the same format the models must produce. Real start of `data/truth/HML.csv`:

```
date,value
192607,-2.75
192608,4.13
```

Last, it saves the whole comparison table to `data/ground_truth_results.csv` and prints it with 4 decimals.

```python
if __name__ == "__main__":
    sys.exit(main())
```

This standard Python idiom means "run `main()` only when this file is run directly, not when another file imports it". `score.py` does `import ground_truth as gt` to reuse the recipes, and this line stops that import from rerunning everything.

## If something goes wrong

- **`FileNotFoundError: ... data/raw/6_Portfolios_2x3.csv`** - the raw CSVs are not in `data/raw/`. Check you are in the project folder, or pass `--raw path/to/raw`. The download URL pattern is in `tasks.json` (`url_pattern`).
- **`KeyError: "no block titled like 'Value Weighted Returns -- Monthly' ..."`** - a raw file is not the expected Ken French format (for example, an HTML error page saved as `.csv`). Run `python -I ground_truth.py --blocks` to see what tables the parser found.
- **`AssertionError` from `_smb3`** - a file's column names changed, so the code did not find exactly 3 small and 3 big portfolios. Compare the header line in the file with the names in the recipe.
- **RMSE suddenly well above 1 bp for a task** - most likely the raw files and the official files come from different CRSP releases (French updates them). Download all files on the same day.

## Check your understanding

1. Why does HML average a small and a big portfolio on each side, instead of just using all value stocks minus all growth stocks?
2. Why is ST_REV computed as Low minus High, while MOM is High minus Low?
3. Why is the human rebuild off by about 0.29 bp RMSE instead of exactly 0?

<details>
<summary>Answers</summary>

1. To keep the factor roughly size-neutral. Small and big stocks behave differently. Averaging the small value-minus-growth spread with the big one gives each size group equal weight, so HML measures value, not size.
2. The factor is defined as the strategy that profits from the effect. Momentum: past winners keep winning, so long winners (High). Reversal: last month's losers bounce back, so long losers (Low).
3. The official factors are rounded to 2 decimals (1 bp steps). Rounding errors spread evenly over plus or minus 0.5 bp, and the RMS of that is about 1/sqrt(12) = 0.29 bp. It is rounding noise, not a recipe error.

</details>
