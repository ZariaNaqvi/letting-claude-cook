# 4. The data and its traps

Everything comes from the **Ken French Data Library**:
https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html

Each file downloads as a zip from
`https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/<NAME>_CSV.zip`.
The version checked for this project is built from the **202608 CRSP release** (data through August 2026). It was downloaded on Oct 14, 2026.

## The 11 files and what each is for

### Answer files (official factors, which the models never use to build their answer)

| File | Columns used | Monthly range |
|---|---|---|
| `F-F_Research_Data_Factors.csv` | SMB (3-factor), HML | 1926-07 to 2026-08 (1,202 months) |
| `F-F_Research_Data_5_Factors_2x3.csv` | SMB (5-factor), RMW, CMA | 1963-07 to 2026-08 (758 months) |
| `F-F_Momentum_Factor.csv` | Mom | 1927-01 to 2026-08 (1,196 months) |
| `F-F_ST_Reversal_Factor.csv` | ST_Rev | 1926-02 to 2026-08 (1,207 months) |
| `F-F_LT_Reversal_Factor.csv` | LT_Rev | 1931-01 to 2026-08 (1,148 months) |

### Input files (the 2 × 3 portfolios the models build from)

| File | Sort | Builds |
|---|---|---|
| `6_Portfolios_2x3.csv` | size × book-to-market | HML, SMB_3F, and part of SMB_5F |
| `6_Portfolios_ME_OP_2x3.csv` | size × operating profitability | RMW, part of SMB_5F |
| `6_Portfolios_ME_INV_2x3.csv` | size × investment | CMA, part of SMB_5F |
| `6_Portfolios_ME_Prior_12_2.csv` | size × past 12-to-2-month return | MOM |
| `6_Portfolios_ME_Prior_1_0.csv` | size × last month's return | ST_REV |
| `6_Portfolios_ME_Prior_60_13.csv` | size × past 60-to-13-month return | LT_REV |

## The 8 recipes (verified)

"S" = small, "B" = big. Every recipe uses the **value-weighted monthly** table.

| Task | Recipe | Your rebuild's error |
|---|---|---|
| HML | ½(S HiBM + B HiBM) − ½(S LoBM + B LoBM) | 0.29 bp |
| SMB_3F | average of 3 small − average of 3 big, size × B/M file only | 0.30 bp |
| SMB_5F | ⅓(SMB from B/M + SMB from OP + SMB from INV), i.e. 9 small vs. 9 big | 0.28 bp |
| RMW | ½(S HiOP + B HiOP) − ½(S LoOP + B LoOP) | 0.29 bp |
| CMA | ½(S LoINV + B LoINV) − ½(S HiINV + B HiINV) | 0.29 bp |
| MOM | ½(S HiPRIOR + B HiPRIOR) − ½(S LoPRIOR + B LoPRIOR) | 0.41 bp |
| ST_REV | ½(S LoPRIOR + B LoPRIOR) − ½(S HiPRIOR + B HiPRIOR) | 0.41 bp |
| LT_REV | ½(S LoPRIOR + B LoPRIOR) − ½(S HiPRIOR + B HiPRIOR) | 0.42 bp |

Note the direction:
- **CMA** is *low* investment minus high, because conservative firms are the "long" side.
- The two **reversal** factors are *losers* minus winners.
- **MOM** is winners minus losers.

## How a 2 × 3 file is laid out

`6_Portfolios_2x3.csv` holds **10 tables stacked vertically**:

| # | Table | Starts at line |
|---|---|---|
| 0 | **Value-weighted monthly returns** ← the one you want | 16 |
| 1 | Equal-weighted monthly returns (same column names!) | 1222 |
| 2 | Value-weighted annual returns | 2428 |
| 3 | Equal-weighted annual returns | 2531 |
| 4 | Number of firms | 2635 |
| 5 | Average market cap | 3841 |
| 6–9 | Book-to-market, OP, INV characteristics | later |

The column names are `SMALL LoBM, ME1 BM2, SMALL HiBM, BIG LoBM, ME2 BM2, BIG HiBM`. "HiBM" means high book-to-market, which is **value**. "LoBM" is **growth**.

The three Prior files have 8 tables and use the columns `SMALL LoPRIOR, ME1 PRIOR2, SMALL HiPRIOR, BIG LoPRIOR, ME2 PRIOR2, BIG HiPRIOR`.

## The traps (each one checked on the real files)

| # | Trap | What goes wrong | Size of the error |
|---|---|---|---|
| 1 | **Stacked tables with identical headers** | Code grabs the equal-weighted table | HML off by about 137 bp, correlation 0.93 |
| 2 | **Annual rows in the same file** | `1927` rows mixed in with `192701` rows | Bad dates, wrong averages |
| 3 | **Malformed rows** in the Prior files' equal-weighted tables (8 or 9 fields under a 6-column header) | A plain `pd.read_csv` on the whole file crashes | CRASH |
| 4 | **Stray carriage returns** (`\r`) in `6_Portfolios_2x3.csv` | Lines split in odd places, so line numbers shift | Parser confusion |
| 5 | **Mixed line endings** in the ST reversal file | Same as above | Parser confusion |
| 6 | **Header on a different line in each file** (11, 16, 17 or 23) | A hard-coded `skiprows=` works on one file and breaks on the next | Wrong table or crash |
| 7 | **Sign conventions** | Reversal computed as winners − losers | Correlation −1, about 700 bp (about 950 bp for MOM) |
| 8 | **Two different SMBs** | 3-factor recipe used for SMB_5F, or the reverse | About 60 bp, correlation 0.98 |
| 9 | **Different start dates and decimals** | 2×3 files use 4 decimals, Prior files 2 | Coverage/precision mistakes |
| 10 | **Label translation** | Must know HiBM = value, LoOP = weak, LoINV = conservative | Formula backwards |
| 11 | **Missing-value codes** (-99.99, -999) are mentioned in the headers | They don't actually appear in these files, but robust code should handle them | None, if handled |

**Why this is good for the experiment:** a model that only pattern-matches ("find a table, subtract two columns") falls into traps 1, 6 and 7. A model that reads carefully and knows the finance avoids them. Those are the differences you want the benchmark to measure.

**For the talk:** traps 1, 7 and 8 make great slides. Each is one plausible-looking mistake with a big, measurable error.

Next: [05 — Glossary](05-glossary.md)
