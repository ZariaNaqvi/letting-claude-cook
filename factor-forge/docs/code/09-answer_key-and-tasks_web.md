# 09 - `web/answer_key.py` and `web/tasks_web.json`

## In one sentence

`tasks_web.json` defines the 8 Part 3 tasks, and `answer_key.py` builds and freezes their exact answers from SEC's XBRL API, which the models can't reach.

## Why they exist

Part 2's answer key was Ken French's official series. Part 3 needs one too: the exact book equity in each filing. It must come from a source **separate** from the pages the models read, or the test would be circular. SEC publishes every tagged number in a filing through `data.sec.gov/api/xbrl`. The harness blocks that API for the models (see [10](10-sec_policy.md)), so the key and the pages are independent.

The key also records **look-alike numbers** (the comparative column, equity including NCI, total liabilities and equity, preferred stock, later filings that repeat the number). The scorer uses them to name each mistake.

## How to run it

From `~/letting-claude-cook/factor-forge` with the venv active:

```bash
python web/answer_key.py --check     # no network: verify the raw files and the frozen key
python web/answer_key.py --rebuild   # no network: rebuild the key from the raw files
python web/answer_key.py --force     # 11 SEC requests: refetch and overwrite (needs SEC_USER_AGENT)
```

Without `--force`, a fetch refuses to overwrite: `web/answer_key.json exists (frozen). Use --check, or --force to refetch and overwrite.`

Real output of `--check` (Oct 28, shortened):

```
sha256 OK for 11 raw files

task  entity                                value_usd accession              form  filed      end
T1    Apple Inc.                      107,520,000,000 0000320193-26-000020   10-Q  2026-07-31 2026-06-27
      look-alikes: {'total_liabilities_and_equity': 383266000000, 'total_assets': 383266000000}  other periods: {... '2025-09-27': 73733000000, '2026-03-28': 106491000000}  later same-value filings: []
T4    Netflix, Inc.                    30,152,052,000 0001065280-26-000212   10-Q  2026-07-17 2026-06-30
      ... later same-value filings: ['0001065280-26-000291']
T6    JPMORGAN CHASE & CO             353,558,000,000 0001628280-26-054343   10-Q  2026-08-06 2026-06-30  (SE 374,598,000,000 - preferred 21,040,000,000)
T8    ranking high->low B/M: ['CVX', 'KO', 'MMM', 'AAPL']

frozen key matches a rebuild from raw files: True
```

## What it reads and writes

| | |
|---|---|
| reads | `web/tasks_web.json`; with `--force`, 10 companyfacts files + 1 frames file from `data.sec.gov` |
| writes | `web/data/raw/*.json.gz` (raw responses), `web/data/raw/manifest.json` (url, fetch time, sha256, bytes), `web/answer_key.json` (the frozen key), and the `answer` blocks and T8 `market_equity.usd` in `tasks_web.json` |

## Walkthrough

1. **`all_ciks`** lists the 10 companies (7 single tasks + KO, CVX, MMM for T8; Apple is in both).
2. **`fetch_all`** (only with `--force` or a first fetch) downloads each URL 0.3 s apart with the declared User-Agent, gzips the body and records its sha256.
3. **`read_raw`** reads a raw file back and stops with `sha256 mismatch` if it changed.
4. **`pick`** finds the `StockholdersEquity` fact with the task's `target_end`, a form in `allowed_forms`, filed inside `filed_window` (2026-07-01 to 2026-08-31), and takes the **earliest filed**. That is the original filing, not a later one that repeats the number as a comparative.
5. **`firm_key`** adds the look-alikes: other dates in the same filing, the prior period, `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest`, `LiabilitiesAndStockholdersEquity`, `Assets`, preferred stock (three possible XBRL names, because JPM uses a different one), later filings with the same value, amendments, and the cover-page share count.
6. **T6** (`kind: common`): value = total equity − preferred. It also stores "preferred not subtracted" and "SE minus liquidation preference" as look-alikes.
7. **T8** (`kind: rank`): book equity per firm, market equity = cover shares × the June 30 close in `tasks_web.json`, B/M = BE/ME, ranking high to low.
8. **`--check`** rebuilds the key from the raw files and compares it with the frozen file.

## `tasks_web.json` fields

| field | meaning |
|---|---|
| `general_rules` | whole USD, accession `##########-##-######`, `period_end` YYYY-MM-DD, book equity = parent's total equity |
| `filed_window` | `["2026-07-01", "2026-08-31"]` |
| `single_schema`, `rank_schema` | the `submit_answer` input schemas (T1–T7, T8) |
| per task | `id`, `kind` (`single`, `common`, `rank`), `firm`, `cik`, `target_end`, `allowed_forms`, `max_steps` (30, T8 50), `goal`, `steps` (the STEPS click path), `units_hint`, `answer` (written by `answer_key.py`; don't edit by hand), `tolerance_usd` 0 |
| T8 | `firms` (ticker, CIK, target end) and `market_equity` (source text, closes, frozen `usd`) |

## Things to check

- The `steps` text for T2, T3 and T5–T8 has not been walked live yet. Check it in Step 14 before freezing the prompts.
- The key was frozen with the test User-Agent. The numbers don't depend on it.
