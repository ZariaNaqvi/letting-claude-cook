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

---

# Part 3: the SEC EDGAR site and its traps

In Part 3 the "data" is a website: **SEC EDGAR** (https://www.sec.gov), where US public companies file their reports. The models reach it only through a headless browser and 9 tools. Everything below was checked on the live site on Oct 28, 2026 (fully for T1 and T4; the labels for T2, T3 and T5–T8 are checked in Step 14).

## The click path (T1, Apple)

| # | Page | What the model does |
|---|---|---|
| 1 | `https://www.sec.gov/search-filings` | Types "Apple Inc" in the box "Name, ticker symbol, or CIK" and clicks the suggestion "Apple Inc. (AAPL)" |
| 2 | Company page `/edgar/browse/?CIK=320193` | The filings table is built by JavaScript (its raw HTML holds 0 accession numbers). Expands "10-K (annual reports) and 10-Q (quarterly reports)" |
| 3 | The filings list | Finds the 10-Q filed 2026-07-31 among many Form 4 and Form 144 insider filings; clicks "Filing" |
| 4 | Filing index | Reads "SEC Accession No." 0000320193-26-000020 |
| 5 | Folder `/Archives/edgar/data/320193/000032019326000020/` | Opens `FilingSummary.xml` and finds "CONDENSED CONSOLIDATED BALANCE SHEETS (Unaudited)" → `R4.htm` |
| 6 | `R4.htm` | Row "Total shareholders' equity", column "Jun. 27, 2026": **107,520** ($ in millions) → 107,520,000,000 |

## What the model can and cannot reach

| Allowed | Blocked |
|---|---|
| `www.sec.gov` pages that SEC's robots.txt allows (`/Archives/edgar/data` is allowed) | `data.sec.gov/api/xbrl/*`: the answer-key source |
| `efts.sec.gov` (the company-name autocomplete and search) | `www.sec.gov/cgi-bin/*` (classic browse and the Interactive Data viewer), `/search/` and the other robots.txt `Disallow` lines |
| `data.sec.gov/submissions/*` (the filings-list JSON the company page loads; no balance-sheet numbers) | every other site (FRED, Yahoo, Wikipedia, ...) as a page |
| jQuery, Bootstrap and DataTables from public CDNs, but **only** as scripts or stylesheets of an SEC page | images, media and fonts (skipped to save traffic) |

Shortcuts left open on purpose: the filing's own XBRL instance file (`*_htm.xml`) and the inline viewer (`/ix?doc=`) sit inside the filing folder. Typing a URL directly is allowed too; the scorer records whether the search form was used (`visited_search_form`).

## The 8 tasks and their keys

| Task | Firm | Key (whole USD) | Accession | Period end | Main trap |
|---|---|---|---|---|---|
| T1 | Apple | 107,520,000,000 | 0000320193-26-000020 | 2026-06-27 | Form 4/144 noise; Sep. 27, 2025 comparative column |
| T2 | Microsoft | 442,387,000,000 | 0001193125-26-323660 (10-K) | 2026-06-30 | June 30 is the fiscal year-end, so it's a **10-K**; the later 10-Q repeats the number |
| T3 | Walmart | 98,238,000,000 | 0000104169-26-000154 | 2026-07-31 | "Total Walmart shareholders' equity" vs the NCI-inclusive row below it (104,506,000,000); fiscal 2027 |
| T4 | Netflix | 30,152,052,000 | 0001065280-26-000212 | 2026-06-30 | **$ in thousands**; the October 10-Q (…-000291) repeats the number |
| T5 | Domino's | −3,982,431,000 | 0001286681-26-000035 | 2026-06-14 | A **deficit** shown as (3,982,431), in thousands; odd quarter-end |
| T6 | JPMorgan | 353,558,000,000 | 0001628280-26-054343 | 2026-06-30 | Common equity = total 374,598,000,000 **minus** preferred 21,040,000,000; a very long bank balance sheet |
| T7 | Berkshire Hathaway | 747,910,000,000 | 0001193125-26-341032 | 2026-06-30 | Two-part balance sheet; NCI row (750,177,000,000); look-alike companies in search |
| T8 | Apple, Coca-Cola, Chevron, 3M | AAPL 107,520,000,000; KO 36,150,000,000; CVX 189,883,000,000; MMM 2,952,000,000 | not checked | KO 2026-07-03, others 06-27/06-30 | Four click paths in 40 steps; ranking by B/M: **CVX, KO, MMM, AAPL** |

T8's market equity is given in the prompt: shares outstanding on each 10-Q cover × the June 30, 2026 close (AAPL $4,222,971,924,800; KO $349,668,176,979; CVX $327,503,846,378; MMM $83,500,616,536).

## The traps

| # | Trap | What goes wrong | Tag |
|---|---|---|---|
| 1 | **Many dependent pages** (search → company → filings → index → FilingSummary → R page) | One wrong click and the rest of the path is wrong; the model runs out of steps | NAV_ERROR, STEP_LIMIT |
| 2 | **JavaScript filings table** | A model that reads too early sees no filings | NAV_ERROR, GAVE_UP |
| 3 | **Insider-trading noise** (Form 4, Form 144) | The 10-Q is hard to spot in the list | NAV_ERROR |
| 4 | **Comparative column** (prior year-end next to this quarter) | Takes Apple's Sep. 27, 2025 value 73,733,000,000 | WRONG_PERIOD |
| 5 | **Look-alike rows** | Total liabilities and equity (Apple 383,266,000,000), equity incl. NCI | WRONG_LINE |
| 6 | **Units** | Submits 107,520 or 30,152,052 instead of whole dollars | UNITS |
| 7 | **Fiscal calendars** | Looks for Microsoft's June 10-Q (there is none); misreads Walmart's FY2027 | NAV_ERROR, WRONG_FILING |
| 8 | **Sign** | Domino's deficit submitted as a positive number | SIGN |
| 9 | **Preferred stock** (T6) | Forgets to subtract it, or subtracts the liquidation preference (21,200,000,000) instead | WRONG_LINE |
| 10 | **Later filings repeat the number** | Right value, but the accession of the October 10-Q | WRONG_FILING |
| 11 | **Look-alike companies** (Berkshire Hathaway Energy, BH Finance) | The path is followed for the wrong entity | WRONG_ENTITY |
| 12 | **Long pages** | Bank and Berkshire balance sheets span several 10,000-character chunks; must use `read_page(page=n)` or `find_text` | STEP_LIMIT, WRONG_LINE |
| 13 | **Post-cutoff values** | A model that "remembers" a number is guessing | UNGROUNDED |

**For the talk:** traps 4, 6 and 9 are one-slide stories: a plausible-looking number, one row or column away, and an exact dollar error.

## What we learned about the site while building (Oct 28)

- **SEC blocks headless Chromium's own requests** (`403 Undeclared Automated Tool`), even with a declared User-Agent. A plain HTTP client with the same User-Agent gets 200. So every request goes through `httpx2`, and Chromium only renders.
- **The company page needs CDN libraries** (jQuery, Bootstrap, DataTables) to build the filings table.
- **Rare stalls of about 690 s** happened three times while loading one SEC script. Each request now has a 25 s cap, and a tool call slower than 120 s is not counted against the model's 12 minutes. The root cause is not known.
- **Netflix's original 10-Q** is …-000212 (filed 2026-07-17), not …-000291 as the first design said; -000291 is the October 10-Q.

Next: [05 — Glossary](05-glossary.md)
