# 14 - `web/mock_agent.py`, `web/capture_fixtures.py` and `web/selftest_web.py`

## In one sentence

A fake model with 9 personas, a recorder that saves the live pages once, and a self-test that checks the whole Part 3 pipeline with no API and no network.

## Why they exist

Same idea as Part 2's `dryrun_mock.py` and `selftest.py`: plant mistakes you know, and check the scorer names each one, before spending money.

## `mock_agent.py`

`MockModel` has the same interface as the real caller: it gets the messages and returns `tool_use` blocks. It really drives the browser: it finds refs by the text on the page, reads the accession off the filing index, opens `FilingSummary.xml`, finds the balance-sheet page and reads the number.

| persona | what it does | tag the scorer must give |
|---|---|---|
| `good` | follows STEPS, right row and column, converts units | PASS |
| `api` | tries `data.sec.gov/api/xbrl` first (blocked), then as good | PASS, `blocked_attempts` > 0 |
| `comparative` | takes the other date column | WRONG_PERIOD |
| `units` | submits the number as printed | UNITS |
| `wrong_line` | takes "Total liabilities and ... equity" | WRONG_LINE |
| `wrong_entity` | does the path for a different company | WRONG_ENTITY |
| `hallucinate` | answers at step 2 with a made-up number | UNGROUNDED |
| `give_up` | opens the search page, then gives up | GAVE_UP |
| `loop` | re-reads the same page until the cap | STEP_LIMIT |

On T8 (four firms), `comparative` and `units` make their mistake on all four firms. `wrong_line` and `wrong_entity` make it on the first firm (Apple) only, and the other three are right, so the scorer's worst-firm rule gets tested. The good path is 10 calls per firm plus `submit_answer`: 41 calls (cap 50). If the target date isn't one of an R page's column headers, the mock gives up instead of guessing a column.

`FIRMS` at the top holds the labels a careful human reads (search text, suggestion, form, period, row). If the live labels differ, fix them here **and** in `tasks_web.json`. This file is never shown to the models.

## `capture_fixtures.py`

```bash
python web/capture_fixtures.py --tasks T1 T4     # done Oct 28
python web/capture_fixtures.py --all             # Step 14, before the pilot
```

It walks each task with the `good` persona in record mode and saves every response to `web/fixtures/` (`index.json` + one file per response). It needs `SEC_USER_AGENT` (the test value is accepted). Real output (Oct 28):

```
T1: Apple Inc.
   1 goto ...
  11 submit_answer {'value_usd': 107520000000, 'accession': '0000320193-26-000020', 'period_end': '2026-06-27', ...}
  -> matches the key; 41 network requests; max 5 requests in any 1 s window
T4: Netflix, Inc.
  -> matches the key; 39 network requests; max 4 requests in any 1 s window

fixtures: 69 saved responses in .../web/fixtures
```

Exit code 1 if any task `DOES NOT match the key` (fix its labels), 2 if SEC answered 403.

## `selftest_web.py`

```bash
python web/selftest_web.py
```

No API calls, no network, 1–3 minutes. Sections:

| | checks |
|---|---|
| A | policy: XBRL API, `/cgi-bin`, `/search/`, FRED and Yahoo blocked; R pages, the company page, `search-filings`, submissions JSON and efts allowed (12 checks) |
| B | 16 requests → at most 5 in any 1 s window |
| C | refuses to start without `SEC_USER_AGENT`, with the placeholder, and with the test value for paid runs |
| D | every planted mistake on all 8 tasks, on synthetic pages built from the key (PASS, UNITS, SIGN, UNGROUNDED, WRONG_FILING, NAV_ERROR, GAVE_UP, STEP_LIMIT, TIME_LIMIT, REFUSAL, HARNESS_ERROR, WRONG_PERIOD, WRONG_LINE, WRONG_ENTITY; T6 ARITH; T8 PASS/ARITH/UNITS/WRONG_PERIOD/UNGROUNDED) |
| F | the real `ClaudeCaller` against a fake HTTP server: effort high, top-level and system-prompt `cache_control`, system prompt, streaming, no temperature/tool_choice/thinking, 9 tools, thinking + signature sent back on turn 2, the cost formula, the spend ledger keeping redone runs' cost |
| G | redirects in the real headless browser with a fake HTTP transport: the page lands on the final URL, relative links resolve against it, the final page is fetched once, a redirect into the XBRL API is blocked |
| H | T8: all 9 personas on a fake site (no browser, no fixtures): `good` finishes in 41 of 50 calls, `api` in 42; comparative/units are wrong on all four firms, wrong_line/wrong_entity on Apple only; loop hits the cap |
| E | all 9 personas on T1 and T4 through the real harness and browser, offline, with 0 network requests |

Real output (Oct 28, end):

```
ok  T4 wrong_line    -> WRONG_LINE    (want WRONG_LINE; blocked=0, network=0)
ok  18 offline runs scored

148/148 checks passed
ALL CHECKS PASSED
```

Section E needs the fixtures; without them it warns and fails.
