# 6. Part 3 design: Form Forge (book equity through the SEC EDGAR web forms)

*Written 2026-10-28. Status: **built and tested on 2026-10-28** with a fake model only (no API calls, no paid runs). Where the build differs from the first draft, this file now describes what was built; §13 lists every change and the real test outputs. The old Part 3 (analysis, write-up, talk) becomes **Part 4**. The Nov 11 deadline does not move.*

---

## 0. One-paragraph summary

In Part 2 every model rebuilt Ken French factors from tidy CSV previews, and they **tied**: 316/320 PASS. The four failures were careless coding slips, not finance mistakes. Part 3 makes the job harder in the way real research is hard. The model gets **no files and no Python**. It gets only a headless web browser, driven through tools, and must **click through SEC EDGAR**: the company search form, then the filings table, then the filing index, then the financial-report (R) pages. From there it pulls **book equity**, the "B" in B/M behind HML, out of 10-Q and 10-K balance sheets **filed after July 1, 2026**, which is past every model's training cutoff. The answer key comes from a separate SEC source, the XBRL `companyfacts` API. The models' browser cannot reach that API, so they must use the forms. Grading is still exact and automatic: same 4 models, same effort, two conditions, repeats, and error tags, as in Part 2.

---

## 1. Why this site (and not the others)

| Candidate (all checked live 2026-10-28) | SkyServer-like? | Exact independent key | Post-cutoff data | Policy | Link to Factor Forge | Verdict |
|---|---|---|---|---|---|---|
| **SEC EDGAR: company search, filings table, filing index, R pages** | Yes. Several dependent pages, a JS filings table, and long financial pages | Yes. `data.sec.gov/api/xbrl/companyfacts` gives Apple 107,520,000,000, which exactly matches R4.htm "107,520" ($ millions) | Yes. 10-Qs filed Jul–Aug 2026 | `/Archives/edgar/data` is allowed and `/cgi-bin` is disallowed. Limit is 10 req/s with a declared UA | **Strongest.** Book equity is the raw input of HML/RMW/CMA | **Primary** |
| Fed DDP "Build Your Package" (H.15) | Closest form flow (ASP.NET ViewState wizard) | Yes (CSV) | Yes | **The wizard is being removed the week of Nov 9, 2026** (notice on the live page) | Moderate (the RF leg) | Rejected: it disappears before the deadline and can't be reproduced |
| NY Fed reference-rates search (SOFR) | One JS search form | Yes (Markets API) | Yes | OK | Moderate (RF) | Backup if SEC access breaks |
| BLS multi-screen CPI wizard | Very (6 screens) | Yes | Yes | `data.bls.gov/robots.txt` = `Disallow: /` | Weak | Rejected on policy |
| home.treasury.gov yield tables, FRED, BEA iTable, FiscalData | One-level forms, or the model knows the URL scheme | Yes | Yes | OK | Weak–moderate | Too easy (FRED) or too far from factors |

**Decision:** SEC EDGAR is the one primary site. If SEC blocks the harness during the run (for example, HTTP 403 on every page), switch to the NY Fed SOFR search as a fallback task family, keeping the same harness and conditions. Write the switch down in `notes.txt` as a protocol deviation.

---

## 2. Name, research question, hypotheses

**Part 3 name:** *Form Forge*, still inside `factor-forge/`.

**Research question:** Part 2 handed the models clean files, and they tied. When they must **find** the same kind of input themselves, by clicking through a real, messy government website, do they still tie? Or do model size and explicit instructions start to matter?

| # | Hypothesis | Builds on Part 2 | Test |
|---|---|---|---|
| **H1 (ceiling breaks)** | The overall pass rate drops well below Part 2's 98.8%. Prediction: under 80% | 316/320 was a ceiling, not a measurement | Pass rate with Wilson 95% CI vs 316/320 (Fisher) |
| **H2 (bigger = better, retested)** | With the ceiling gone, pass rates order Fable ≥ Opus ≥ Sonnet ≥ Haiku, and Fable beats Haiku | H1 in Part 2 was rejected (Sonnet 80/80 was top) | Fisher exact, Fable vs Haiku and Opus vs Sonnet; per-model Wilson CIs |
| **H3 (instructions matter more)** | STEPS beats GOAL_ONLY by more than Part 2's RECIPE − NAME_ONLY gap (160/160 vs 156/160) | In Part 2, all 4 failures came without a recipe | Fisher pooled across models; the gap per model |
| **H4 (failures change type)** | Most failures are finance or navigation mistakes (WRONG_LINE, WRONG_PERIOD, UNITS, NAV_ERROR), not coding slips or step limits | Part 2's failures were empty-output and pandas crashes | Error-tag table; the share of failures in the finance/navigation tags |
| **H5 (efficiency)** | Bigger models need fewer steps per success but cost more per correct answer. Haiku stays the cheapest per correct answer | Part 2: Haiku was nearly free and nearly perfect | Median steps per success; total $ ÷ passes per model |

### Why it is harder than Part 2

1. **Multi-step navigation with state.** The data sits 4–7 dependent pages deep: search form, company page, filings table filtered by form type, filing index, FilingSummary.xml or the R-page menu, and finally the balance-sheet page. Each step depends on what the previous page showed.
2. **JavaScript pages.** The company filings table (`/edgar/browse/?CIK=`) is filled by JavaScript. Its static HTML has 0 accession numbers, so the agent must wait for it and read the rendered table.
3. **Noise and distractors.** Apple's recent filings are mostly Form 4 and Form 144 entries (insider trades). The 10-Q is buried among them, and new Q3 filings (10-Qs, Apple's FY2026 10-K) appear during the run window.
4. **Look-alike numbers on the same page.** The prior-year-end comparative column, "Total liabilities and shareholders' equity" one row down, equity *including* noncontrolling interests, and preferred stock inside total equity.
5. **Units.** "$ in Millions" vs "$ in Thousands" (Netflix, Domino's) vs whole dollars in the answer.
6. **Fiscal calendars.** Apple's "Q3 FY2026" ends Jun 27, Walmart's Q2 FY2027 ends Jul 31, and Microsoft's June 30 date is a **10-K**, not a 10-Q.
7. **Sign conventions.** Domino's has a stockholders' *deficit*, shown in parentheses.
8. **Long pages.** Bank and Berkshire balance sheets run to many rows, and the full 10-Q document is hundreds of KB. Observations are trimmed, so the model must page or search.
9. **Post-cutoff values.** Every answer was filed after 2026-07-01, so recall cannot help. The `UNGROUNDED` tag catches guesses.

---

## 3. Agent harness design

### 3.1 How it works

```
run_web.py ──(Messages API, tool use)──► model
     ▲                                   │ tool_use: goto / click / fill / ...
     │ tool_result: trimmed page text    ▼
     └──────────── browser_tools.py ── Playwright headless Chromium ── sec_policy.py (allowlist, robots, rate limit, UA)
                         │
                         └── runs_web/<run_id>/steps.jsonl, pages/*.txt, final.json
```

* **Tool use through the Claude Messages API.** The harness defines the tools, and the model can act only through them. It has **no** code execution and no fetch tool.
* **How requests reach SEC:** every request the page makes goes through `sec_policy.Policy.handle`. Allowed requests are made by a plain HTTP client (`httpx2`) that sends **only** the declared User-Agent, follows redirects itself (checking each one against the policy) and waits for the rate limiter on every hop. Chromium only renders the answer. (Headless Chromium fetching SEC pages itself got `403 Undeclared Automated Tool`.) Nothing is disguised.
* **The browser:** Python + Playwright 1.64.1, headless Chromium, viewport 1280×1600. Each run gets a **fresh browser context** (no cookies, no history), so runs cannot leak into each other.
* **The same for every model:** the same system prompt, tools, limits, effort (`high`), and `max_tokens` per turn (**16,000**; thinking counts toward it, and 4,000 risked cutting turns off. Billing is for tokens actually produced, so it does not raise cost). Model IDs and prices are imported from `run_experiment.py`'s `MODELS` dict, read only, so Part 2 is unchanged.

### 3.2 The tools (identical for all models)

| Tool | Arguments | What it returns |
|---|---|---|
| `goto` | `url` | Loads the page (waits for `networkidle`, max 20 s) and returns a `read_page` snapshot. Allowed hosts only (§3.3) |
| `read_page` | `page` (int, default 1) | Rendered visible text with refs marked inline, e.g. `[e12 link] 10-Q`, `[e3 textbox "Company name or ticker" value=""]`. It is cut into chunks of ≤ 10,000 characters (about 2,500 tokens; hard cap 10,800 per tool result). Header line: `URL: … \| TITLE: … \| chunk 1/4` |
| `find_text` | `query` | Up to 20 matching lines with ±1 line of context, plus their chunk numbers. This is for long R pages and 10-Q documents |
| `click` | `ref` | Clicks the element, waits, and returns a snapshot. A link to a blocked URL returns `BLOCKED: <reason>` |
| `fill` | `ref`, `text` | Types into an input and returns a short confirmation plus any autocomplete options as refs |
| `select_option` | `ref`, `value` | For `<select>` elements |
| `press` | `key` (`Enter`, `Tab`, `Escape`, `ArrowDown`, `ArrowUp`) | Returns a snapshot |
| `back` | (none) | Browser back, then a snapshot |
| `submit_answer` | task-specific JSON (§4), plus optional `give_up: true` and `evidence_url` | Ends the run |

**Element refs.** On every snapshot, the harness runs a small JS snippet that gives every visible `a[href], button, input, select, textarea, [role=button], [role=link], [role=tab], [role=option], summary` a `data-ff-ref="eN"` attribute. Then `click(ref)` = `page.locator('[data-ff-ref="eN"]').click()`. Refs stay the same while the page stays the same and are renumbered after a navigation; the model is told to use only refs from the latest observation. An unknown ref returns `ERROR: unknown ref eN, call read_page`.

**Limits.**

| Limit | Value | Why |
|---|---|---|
| Tool calls per run | **30** (T1–T7), **40** (T8, four firms) | Enough for the click path ×2 and stops loops. Hitting it = `STEP_LIMIT` |
| Observation size | ≤ 2,500 tokens per tool result | Keeps the context under ~85K tokens, below Haiku's 100K long-prompt price step |
| Wall clock | 12 min per run | `TIME_LIMIT` |
| Page load | 20 s, one automatic retry; each HTTP request is capped at 25 s | A site hiccup is logged as `site_error`. 3 site errors in a run = `HARNESS_ERROR` |
| Stalls | A tool call slower than 120 s | Logged (`n_stalls`, `stall_s`) and **not** counted toward the 12-minute limit |
| Turns without a tool call | The run ends (`no_tool_call`); if no answer, `GAVE_UP`. After a `max_tokens` stop the model gets up to 2 nudges to call a tool | Same rule for all |

**Prompt caching.** `cache_control: {"type": "ephemeral"}` goes on the system prompt plus tool definitions, and on the newest message each turn (incremental caching). The cost model in §6 assumes this. Cached tokens are logged so the estimate can be checked. Old observations are **not** pruned, since pruning would break the cache and hide evidence from the grounding check.

### 3.3 Access policy (`sec_policy.py`): forcing the forms, respecting SEC rules

Every request the browser makes (pages *and* sub-resources) goes through `context.route("**/*", handler)`.

| Rule | Detail |
|---|---|
| **Allowed hosts** | `www.sec.gov`, `efts.sec.gov` (the company-name autocomplete and full-text search the forms call), `data.sec.gov/submissions/*` (the JSON the JS filings table loads; it holds filing lists, no balance-sheet numbers) |
| **Blocked: the answer-key source** | `data.sec.gov/api/xbrl/*` (companyfacts, companyconcept, frames). Blocking it forces the model through the pages. Every blocked attempt is logged as `blocked_attempts` |
| **Blocked: robots.txt** | `www.sec.gov/cgi-bin/*` (classic browse-edgar and the Financial Report viewer), `/search/`, `/Archives/bin`, `/Archives/etc`, `/Archives/usr`, and the other `Disallow` lines in SEC robots.txt (checked 2026-10-28; `Allow: /Archives/edgar/data`) |
| **Page libraries** | jQuery, Bootstrap and DataTables from `code.jquery.com`, `cdnjs.cloudflare.com`, `stackpath.bootstrapcdn.com`, `cdn.datatables.net`, `cdn.jsdelivr.net`: allowed **only** as scripts/stylesheets of an SEC page (the company page needs them), never as pages |
| **Blocked: everything else** | Any other host (FRED, Yahoo, Wikipedia, analytics). Images, media and fonts are also aborted to cut traffic |
| **User-Agent** | Read from `SEC_USER_AGENT` in `.env`. The harness refuses to start if it is missing or still the placeholder. Testing uses `FactorForge-test admin@example.com` |
| **Rate limit** | Global token bucket, **≤ 5 requests/s** across all sub-requests (SEC allows 10). Runs are sequential, never parallel |
| **Static-asset cache** | `.js`/`.css` from `www.sec.gov` and the page libraries are saved once to `web/.asset_cache/` and served locally afterwards, which cuts ~70% of traffic. Page HTML is never cached, so the model always sees the live site |

**Is navigating allowed?** Yes. Typing a URL with `goto` is like using the address bar. A model that knows EDGAR's URL scheme can jump straight to `/edgar/browse/?CIK=320193`, which is fine. It still cannot know a post-cutoff **accession number** without reading the filings table. Shortcuts are measured with `visited_search_form` (true/false) and `blocked_attempts`, not banned.

### 3.4 Logging, one folder per run

`runs_web/<task>__<cond>__<model>__r<k>/`

* `prompt.txt`: the user message the model got
* `steps.jsonl`: one line per tool call: `step, turn, tool, args, url_before, url_after, http_status, blocked (bool), error, obs_chars, obs_tokens_est, obs_sha256, latency_s, input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens`
* `requests.jsonl`: every network request the browser made and the policy's decision (`net 200`, `asset-cache`, `BLOCK …`, `skip`, `fixture`)
* `pages/step_<n>.txt`: the exact observation text the model saw. The `UNGROUNDED` and `NAV_ERROR` checks use these files
* `transcript.json`: the full messages list (thinking blocks are kept only as their type and length; these models return no thinking text)
* `final.json`: answer JSON, stop reason (`answered | gave_up | step_limit | time_limit | no_tool_call | refusal | harness_error`), total tokens, cost, wall time, `blocked_attempts`, `visited_search_form`, harness and prompt versions, `SEC_USER_AGENT` **redacted to its sha256**
* **Resume:** a run folder that already has `final.json` is skipped (except `harness_error` runs, which are redone), so a crash loses at most one run. `final.json` is written last. Dry and real runs can't share an `--out` folder.

### 3.5 Mock model and offline tests (no API calls, no SEC traffic)

* `capture_fixtures.py` walks each task's STEPS path with the `good` persona in record mode (about 40–60 requests per task, ≤ 5 req/s) and saves every response to one shared folder, `web/fixtures/` (`index.json` + one file per response). **On 2026-10-28 only T1 and T4 were captured** (69 saved responses); `--all` must run before the pilot.
* `--offline` mode serves the fixtures through `route.fulfill`, so selftests never touch the network.
* `mock_agent.py` is a fake model with the same tool-use interface. It has scripted personas and plays the role `dryrun_mock.py` played in Part 2:
  * `good`: follows STEPS and submits the key → `PASS`
  * `api`: first tries `data.sec.gov/api/xbrl/...` (BLOCKED), then does as `good` → `PASS` with `blocked_attempts` > 0
  * `comparative`: takes the other date column → `WRONG_PERIOD`
  * `units`: submits the number as printed (millions/thousands) → `UNITS`
  * `wrong_line`: takes "Total liabilities and … equity" → `WRONG_LINE`
  * `wrong_entity`: does the whole path for a different company → `WRONG_ENTITY`
  * `hallucinate`: answers at step 2 with a made-up number → `UNGROUNDED`
  * `give_up`: opens the search page, then gives up → `GAVE_UP`
  * `loop`: keeps re-reading the same page → `STEP_LIMIT`
* `selftest_web.py` (148 checks, no API, no network): A. the policy blocks the API, `/cgi-bin`, `/search/` and other hosts and allows the EDGAR pages; B. the rate limiter holds ≤ 5 req/s; C. the harness refuses to start without `SEC_USER_AGENT`, with the placeholder, or with the test value for paid runs; D. every planted mistake on all 8 tasks gets its tag; F. the real API caller against a fake HTTP server (effort, caching, tools, the thinking + tool_use round trip, the cost formula); E. every persona on T1 and T4 end to end on the fixtures. **All of this must pass before any paid call.**

---

## 4. Tasks (8)

General rules for all tasks:

* The answer is a whole number of **US dollars**, not millions or thousands.
* The model also submits the **accession number** (`##########-##-######`) and `period_end` (YYYY-MM-DD).
* "Book equity" = the parent's total stockholders' equity line (XBRL `us-gaap:StockholdersEquity`) unless the task says otherwise.

**Answer key (`web/answer_key.py`, independent of the pages the models see):** one `companyfacts` request per company (11 companies, ~11 requests, 0.3 s apart, UA from `.env`), plus one `frames/us-gaap/StockholdersEquity/USD/CY2026Q2I.json` request for the WRONG_ENTITY check. For each task it picks the fact with `end == target_end`, `form in allowed_forms`, `filed >= 2026-07-01`, and the **earliest `filed`** (the original filing, not a later comparative column). It records `val`, `accn`, `form`, `filed`, and a **look-alike table** used for error tagging:

* other `end` dates in the same filing
* `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest`
* `LiabilitiesAndStockholdersEquity`
* `PreferredStockValue`
* the prior quarter's value

The raw JSON is saved under `web/data/raw/` with sha256 and fetch time. `web/answer_key.json` is then **frozen**, and scoring reads only the frozen file.

**Values below:** frozen by `answer_key.py` on 2026-10-28 from companyfacts (earliest filed fact in the Jul 1 – Aug 31 2026 window). `answer_key.py --check` re-verifies them offline. T1 was also checked against R4.htm, and T1 and T4 were reached live by the mock walk. The STEPS **labels** for T2, T3 and T5–T8 are still unverified (checked in §9 Step 3).

**Tolerance: 0.** R pages print exact millions or thousands, so the correct dollar figure is an exact integer.

| ID | Firm (CIK) | Goal text (GOAL_ONLY) | Click path (STEPS) | Key (frozen 2026-10-28) | Main traps |
|---|---|---|---|---|---|
| **T1** | Apple (320193) | Total shareholders' equity at the end of Apple's fiscal quarter that ended in late June 2026, from the quarterly report filed in July 2026 | Company search "Apple Inc" → company page → filter form type **10-Q** → filing dated **2026-07-31** → "Filing" index → open the folder `/Archives/edgar/data/320193/000032019326000020/` → `FilingSummary.xml` → report "CONDENSED CONSOLIDATED BALANCE SHEETS" (R4) → row "Total shareholders' equity", column "Jun. 27, 2026" | **107,520,000,000**; accn 0000320193-26-000020; 10-Q filed 2026-07-31; end 2026-06-27 | Form 4/144 noise; comparative "Sep. 27, 2025" column; "$ in Millions"; total L+E row |
| **T2** | Microsoft (789019) | Total stockholders' equity as of June 30, 2026, from the first periodic report that reports that date | Search "Microsoft" → filter **10-K** (June 30 is MSFT's fiscal year-end; there is no June 10-Q) → 10-K filed late July 2026 → index → FilingSummary → "BALANCE SHEETS" → "Total stockholders' equity", "Jun. 30, 2026" | **442,387,000,000**; accn 0001193125-26-323660 (**10-K**, filed 2026-07-29); end 2026-06-30 | Looking for a 10-Q; the FY27 Q1 10-Q (filed ~late Oct) shows the same June 30 number as a comparative but has the wrong accession (`WRONG_FILING`) |
| **T3** | Walmart (104169) | Total shareholders' equity attributable to Walmart (excluding noncontrolling interest) at the end of its second fiscal quarter of fiscal 2027 | Search "Walmart" → 10-Q filed ~early Sep 2026 → index → FilingSummary → "Condensed Consolidated Balance Sheets" → **"Total Walmart shareholders' equity"**, "Jul. 31, 2026" | **98,238,000,000**; accn 0000104169-26-000154 (filed 2026-08-28); end 2026-07-31 | "Total shareholders' equity" (includes NCI) is the next row; fiscal-year label (FY2027) vs calendar year |
| **T4** | Netflix (1065280) | Total stockholders' equity at June 30, 2026, from the 10-Q for that quarter | Search "Netflix" → 10-Q filed Jul 2026 → index → FilingSummary → "Consolidated Balance Sheets" → "Total stockholders' equity", "Jun. 30, 2026" | **30,152,052,000** (page shows 30,152,052 **in thousands**); accn **0001065280-26-000212** (filed 2026-07-17; the October 10-Q -000291 repeats the number → `WRONG_FILING`) | **Units in thousands**: a model used to millions gives 30,152,052,000,000 or 30,152,052 → `UNITS` |
| **T5** | Domino's Pizza (1286681) | Total stockholders' equity (deficit) at the end of Domino's second fiscal quarter of 2026 | Search "Domino's Pizza" → 10-Q filed Jul 2026 → index → FilingSummary → "Condensed Consolidated Balance Sheets" → "Total stockholders' deficit", column "Jun. 14, 2026" | **−3,982,431,000**; accn 0001286681-26-000035 (filed 2026-07-20); end 2026-06-14 | Negative value shown as (3,982,431) → `SIGN`; thousands; odd quarter-end date |
| **T6** | JPMorgan Chase (19617) | **Common** book equity at June 30, 2026 = total stockholders' equity minus preferred stock, from the Q2 2026 10-Q | Search "JPMorgan Chase" → 10-Q filed ~early Aug 2026 → index → FilingSummary → "Consolidated balance sheets" → "Total stockholders' equity" **minus** "Preferred stock", "Jun. 30, 2026" | **353,558,000,000** = SE 374,598,000,000 − preferred 21,040,000,000 (JPM tags preferred under a different XBRL name; `answer_key.py` tries fallback names); accn 0001628280-26-054343 (filed 2026-08-06) | Forgetting to subtract preferred (`WRONG_LINE`); very long bank balance sheet; arithmetic (`ARITH`) |
| **T7** | Berkshire Hathaway (1067983) | Berkshire Hathaway shareholders' equity (excluding noncontrolling interests) at June 30, 2026 | Search "Berkshire Hathaway Inc" → 10-Q filed ~early Aug 2026 → index → FilingSummary → "Consolidated Balance Sheets" (spans two sections: Insurance and Other; Railroad, Utilities and Energy) → "Total Berkshire Hathaway shareholders' equity", "Jun. 30, 2026" | **747,910,000,000**; accn 0001193125-26-341032 (filed 2026-08-10) | Two-segment balance sheet; NCI line; Class A/B noise; many look-alike entities in search ("Berkshire Hathaway Energy", "BH Finance") → `WRONG_ENTITY` |
| **T8** | Mini value sort: Apple, Coca-Cola (21344), Chevron (93410), 3M (66740) | For each of the four firms, find book equity from the first 10-Q filed Jul 1–Aug 31 2026. Using the market equity values given below, rank the firms by B/M = BE/ME, high (value) to low (growth) | The T1 path ×4: KO column "Jul. 3, 2026"; CVX "Jun. 30, 2026" (Chevron: "Total Chevron Corporation stockholders' equity"); MMM "Jun. 30, 2026" | BE: AAPL 107,520,000,000; KO **36,150,000,000** (accn 0001628280-26-050503); CVX **189,883,000,000** (0000093410-26-000167); MMM **2,952,000,000** (0000066740-26-000246). ME (frozen in `tasks_web.json`) = cover shares outstanding × the 2026-06-30 close (AAPL 289.36, KO 81.27, CVX 165.76, MMM 161.91; Yahoo Finance daily history): AAPL 4,222,971,924,800; KO 349,668,176,979; CVX 327,503,846,378; MMM 83,500,616,536. Ranking: **CVX, KO, MMM, AAPL** | All single-firm traps ×4; KO's Jul 3 quarter-end; the step budget (40) |

**Answer JSON schemas** (they become the `submit_answer` input schema):

* T1–T7: `{"value_usd": int, "accession": str, "period_end": str}`
* T8: `{"book_equity_usd": {"AAPL": int, "KO": int, "CVX": int, "MMM": int}, "ranking_high_to_low_bm": [str, str, str, str]}`

**Before freezing STEPS text (Oct 29):** the student walks every STEPS path by hand once in Chrome. Then `capture_fixtures.py` replays it. Any wording that doesn't match the live page (button labels, report titles) gets fixed **before** the pilot, and `PROMPT_VERSION` is bumped. No prompt changes after the main run starts.

---

## 5. Conditions

| Condition | Mirrors (Part 2) | What the prompt contains |
|---|---|---|
| **STEPS** | RECIPE | Goal text + the numbered click path from §4, the exact row and column labels, and the units reminder |
| **GOAL_ONLY** | NAME_ONLY | Goal text only, plus the general rules (whole USD, accession, period_end). No site map, no row names, no units hint |

Both conditions share the same system prompt:

> "You are a research assistant using a web browser through tools. Data may only be collected through the SEC EDGAR website (www.sec.gov). Some URLs are blocked. Report exactly what the filing shows; do not estimate. When you are certain, call submit_answer. If you cannot find it, call submit_answer with give_up=true."

Both conditions get the same tools and limits. The prompt never mentions XBRL APIs.

---

## 6. Models, run count, cost

**Models:** `fable` (claude-fable-5-1), `opus` (claude-opus-5-5), `sonnet` (claude-sonnet-5-5), `haiku` (claude-haiku-5-5), effort `high` for all. These are the Part 2 `MODELS` entries, with prices from `run_experiment.py`, cached 2026-10-06. **Re-check pricing and cache multipliers before the run.**

**Design:** 8 tasks × 2 conditions × 4 models × **3 repeats = 192 runs**.

**Token model per run** (to be replaced by pilot measurements):

* Fixed prefix (system + tool defs + task): 3,000 tokens
* Each step adds ~2,000 tokens (observation ~1,800 + tool call ~150) and ~500 output tokens (including thinking at high effort)
* Typical steps: 15 (T1–T7), 30 (T8). Caps: 30 / 40
* Caching: new tokens each turn are written at 1.25× input price, and the rest of the context is read at 0.10×

| Scenario | Input tokens processed | Cache-weighted input ("price-equivalent") | Output tokens |
|---|---|---|---|
| T1–T7 typical (15 steps) | ~255K | ~61K | ~7.5K |
| T8 typical / single-firm at cap (30 steps) | ~960K | ~166K | ~15K |
| T8 at cap (40 steps) | ~1.68M | ~261K | ~20K |

**Cost per run ($):**

| Model | $ in/out per 1M | T1–T7 typical | 30-step run | T8 at cap (40) |
|---|---|---|---|---|
| Fable | 10 / 50 | 0.99 | 2.41 | 3.61 |
| Opus | 4 / 20 | 0.39 | 0.96 | 1.44 |
| Sonnet | 2 / 10 | 0.20 | 0.48 | 0.72 |
| Haiku | 0.10 / 0.50 | 0.010 | 0.024 | 0.036 |

**Main-run total (typical):** per model, 42 single-firm runs + 6 T8 runs.

| Model | Runs | Typical $ |
|---|---|---|
| Fable | 48 | 42×0.99 + 6×2.41 = **56.0** |
| Opus | 48 | 42×0.39 + 6×0.96 = **22.1** |
| Sonnet | 48 | 42×0.20 + 6×0.48 = **11.3** |
| Haiku | 48 | 0.42 + 0.14 = **0.6** |
| **Total** | **192** | **≈ $90**, plus pilot ≈ $5 → **≈ $95** |

**Guards, so cost stays near $100:**

1. **Repeat rule after the pilot.** If the pilot's measured mean cost × 192 runs > $100, use **2 repeats** (128 runs, ≈ $60–65). The decision and the numbers go in `notes.txt` *before* the main run.
2. **`--budget-usd 100`.** `run_web.py` sums actual cost after every run and stops cleanly before starting a run that could push past the cap (it uses the 40-step worst case for that model).
3. **Run order is repeat-major.** All tasks × conditions × models for r1 first, then r2, then r3, with models interleaved inside each cell. If the budget stops the run, every model has the same number of complete repeats, and site changes over time hit all models equally.
4. Worst case without guards (every run at its cap) would be ≈ $200. The budget guard makes that impossible.

**Wall time:** about 2–5 min per run at 5 req/s, so 192 runs ≈ 8–14 h, spread over 2–3 sessions (resume-safe).

---

## 7. Scoring (`web/score_web.py`)

**PASS** means all three of these hold:

1. The run ended with `submit_answer` and no `give_up`.
2. `value_usd == key` exactly. For T8, all four `book_equity_usd` must be exact **and** the ranking must be exact.
3. The `accession` is in the key's allowed set: the original filing for that period, plus its 10-Q/A or 10-K/A if one exists. For T8, the accession check is skipped.

Secondary columns: `value_ok` (the number is right even if the accession is wrong), `accn_ok`, `period_ok`, `grounded`.

**Error tags.** A failing run gets the first tag that matches, in this order (as built in `score_web.py`; for T8 the worst per-firm tag in this order is used):

| Tag | Detection |
|---|---|
| `HARNESS_ERROR` | Exception, 3 site errors in a run, or SEC answered 403. **Excluded and rerun**, never counted as a model failure |
| `STEP_LIMIT` | Hit the tool-call cap without an answer |
| `TIME_LIMIT` | Hit the 12-min cap (stalls excluded) |
| `REFUSAL` | The API stopped with `stop_reason` "refusal" |
| `GAVE_UP` | `give_up: true`, or the run ended without a tool call |
| `UNGROUNDED` | The submitted number never appeared in any of the run's `pages/*.txt`. The check tries every display form: dollars, thousands, millions, billions, with and without commas (at least 4 digits). T6 is also grounded if both components appear. Checked **before** NAV_ERROR so a guess is called a guess |
| `WRONG_ENTITY` | The value equals another company's value in the frames snapshot, or the accession belongs to another CIK |
| `NAV_ERROR` | The target accession folder (no dashes) never appeared in any visited URL **and** the accession never appeared in any observation. The model never reached the filing |
| `UNITS` | value / key ∈ {10³, 10⁶, 10⁻³, 10⁻⁶} |
| `SIGN` | value == −key |
| `WRONG_PERIOD` | The value equals the key firm's value at another `end` date (comparative column, prior quarter) |
| `WRONG_LINE` | The value equals a look-alike line for the same period: equity incl. NCI, total liabilities + equity, total assets, preferred alone, preferred not subtracted (T6), or SE minus liquidation preference (T6) |
| `WRONG_FILING` | The value is right but the accession is a later filing's comparative (e.g. MSFT's FY27 Q1 10-Q) |
| `ARITH` | T6/T8 only: all components appear correctly in the observations, but the submitted combination or ranking is wrong |
| `OTHER_WRONG` | Anything else; read these by hand |

Also reported for every run (PASS or not): `grounded`, `blocked_attempts`, `visited_search_form`, `steps`, `cost_usd`, `input/output/cache tokens`, `wall_s`.

**Hand check:** read 20 runs by hand (all `OTHER_WRONG`, plus a random sample of passes and failures) to check the tags, like Part 2's 10-run hand check.

### Statistics (`web/analyze_web.py` → `results_web/`)

* **Pass rate with Wilson 95% CIs:** overall, by model (n = 48), by condition (n = 96), by task, and model × condition.
* **Fisher exact tests:** Fable vs Haiku and Opus vs Sonnet (H2); STEPS vs GOAL_ONLY pooled and per model (H3); and **Part 2 vs Part 3** per model (H1). Example: Sonnet 80/80 in Part 2 vs x/48 here.
* **Error-tag table** (model × tag, condition × tag) and the share of failures in {WRONG_LINE, WRONG_PERIOD, UNITS, SIGN, WRONG_ENTITY, WRONG_FILING, NAV_ERROR} (H4).
* **Efficiency:** median and IQR of steps per **successful** run; tokens per run; **cost per correct answer** = total $ ÷ passes, per model (H5).
* **Behavior:** the share of runs with `blocked_attempts > 0` (tried the API shortcut) and with `visited_search_form`, by model and condition.
* **Figures:** a task × model heatmap (pass counts out of 6), a cost-per-correct bar chart, and a steps-to-success box plot.
* **Part 2 vs Part 3 summary table** for the paper. This one table carries the story.

---

## 8. File layout

```
factor-forge/
├── run_experiment.py, score.py, ...      # Part 2, unchanged (web/ only imports MODELS read-only)
├── .env.example                          # + SEC_USER_AGENT="Your Name your.address@example.edu"  (placeholder)
├── web/
│   ├── README.md                         # how to run Part 3, the commands from §9
│   ├── requirements-web.txt              # -r ../requirements.txt ; playwright==1.64.1 (+ greenlet, pyee)
│   ├── tasks_web.json                    # 8 tasks: goal, steps, schema, target CIK/end/forms, T8 ME values
│   ├── answer_key.py                     # companyfacts + frames -> answer_key.json (frozen) + data/raw/*.json + sha256
│   ├── sec_policy.py                     # allowlist, robots rules, rate limiter, UA loader, asset cache
│   ├── browser_tools.py                  # Playwright wrapper, refs, trimming, tool JSON schemas
│   ├── prompts_web.py                    # system prompt, STEPS / GOAL_ONLY builders, PROMPT_VERSION
│   ├── run_web.py                        # agent loop, caching, budget guard, resume, --dry-run/--offline/--pilot
│   ├── mock_agent.py                     # scripted fake models (personas)
│   ├── capture_fixtures.py               # one-time page snapshots for offline tests
│   ├── selftest_web.py                   # offline asserts, no API, no network
│   ├── score_web.py                      # PASS + tags -> results_web/runs_scored.csv
│   ├── analyze_web.py                    # Wilson, Fisher, cost/correct, figures
│   ├── fixtures/                         # saved responses, index.json (committed; public SEC pages)
│   └── data/raw/                         # answer-key raw JSON (committed, with sha256 manifest)
├── runs_web_mock/   results_web_mock/    # fake-model runs (git-ignored; regenerate with --dry-run)
├── runs_web_pilot/  results_web_pilot/   # pilot
├── runs_web/        results_web/         # main run
└── docs/06-part3-form-forge-design.md (this file), docs/code/09-…15-*.md explainers
```

`.gitignore` additions: `web/.asset_cache/`, `runs_web_mock/`, `results_web_mock/`. Do **not** ignore `runs_web_pilot/` or `runs_web/`, since the logs are evidence. Check that no file contains the real `SEC_USER_AGENT` (it is redacted in `final.json`).

---

## 9. Exact execution steps

Every session starts with `cd ~/letting-claude-cook/factor-forge && source .venv/bin/activate`. List flags take spaces or commas (`--tasks T1 T4` = `--tasks T1,T4`). The same steps, with tick boxes, are Steps 12–18 of [03-step-by-step-checklist.md](03-step-by-step-checklist.md).

**Step 1: setup (Oct 28)**
```bash
pip install -r web/requirements-web.txt
python -m playwright install chromium
# add to .env (your own name + a contact address you choose; never commit .env):
#   SEC_USER_AGENT="Firstname Lastname contact@yourdomain"
pip show playwright | head -2          # Version: 1.64.1 -> notes.txt
```

**Step 2: the answer key (done Oct 28; re-verify)**, no network
```bash
python web/answer_key.py --check       # "sha256 OK for 11 raw files" ... "frozen key matches a rebuild from raw files: True"
python web/answer_key.py --force       # optional: refetch with your own User-Agent (11 requests), then --check again
```
Checkpoints: T1 prints `107,520,000,000 0000320193-26-000020`; T2's form is `10-K`; T6 shows `(SE 374,598,000,000 - preferred 21,040,000,000)`; T8 ranking `['CVX', 'KO', 'MMM', 'AAPL']`.

**Step 3: walk STEPS by hand, capture fixtures (Oct 29)**
```bash
python web/prompts_web.py T2 STEPS     # print a task's prompt; walk it in Chrome (T2, T3, T5-T8)
python web/capture_fixtures.py --all   # each task: "-> matches the key; N network requests; max 5 requests in any 1 s window"
```
Fix any wording that doesn't match the live labels in `tasks_web.json` and in `mock_agent.py`'s `FIRMS`, rerun that task (`--tasks T6`), then set `PROMPT_VERSION = "web-v1"` in `prompts_web.py` and tag `prompts-web-v1`.

**Step 4: free tests (Oct 29)**, $0
```bash
python web/selftest_web.py                                                                    # "148/148 checks passed", "ALL CHECKS PASSED"
python web/run_web.py --dry-run --offline --tasks all --conds STEPS --repeats 1 --out runs_web_mock/offline
python web/score_web.py --runs runs_web_mock/offline --out results_web_mock/offline           # "0 mismatches"
python web/analyze_web.py --in results_web_mock/offline/runs_scored.csv --part2 results/runs_scored.csv --out results_web_mock/offline
```
Checkpoint: every persona gets its expected tag (`good` and `api` PASS on every task).

**Step 5: pilot (Oct 30)**, about $5–7 (32 Haiku/Sonnet runs + 4 Fable/Opus runs)
```bash
python web/run_web.py --pilot --models haiku sonnet --tasks all --conds STEPS GOAL_ONLY --repeats 1 --out runs_web_pilot
python web/run_web.py --pilot --models fable opus --tasks T1 T4 --conds GOAL_ONLY --repeats 1 --out runs_web_pilot
python web/score_web.py --runs runs_web_pilot --out results_web_pilot
python -c "import pandas as pd; d=pd.read_csv('results_web_pilot/runs_scored.csv'); print(d.groupby('model_alias').cost_usd.agg(['count','mean','sum']))"
```
* Read every pilot transcript.
* Record the measured mean cost per run per model in `notes.txt`.
* Apply the repeat rule (§6): if Σ(mean × 48) > $100, use `--repeats 2`.
* Pilot runs are **not** pooled with the main run.

**Step 6: main run (Oct 31 – Nov 1)**, ≤ $100
```bash
caffeinate -i python web/run_web.py --models fable opus sonnet haiku --tasks all --conds STEPS GOAL_ONLY \
       --repeats 3 --effort high --budget-usd 100 --out runs_web 2>&1 | tee -a runlog_web.txt
```
Safe to Ctrl-C and rerun the same command. `BUDGET STOP` = the cap was reached. `SEC returned HTTP 403 ... Stopping ALL runs` = wait 10+ minutes, check `SEC_USER_AGENT`, rerun.

**Step 7: score, hand-check, analyze (Nov 2–3)**
```bash
python web/score_web.py --runs runs_web --out results_web
python web/analyze_web.py --in results_web/runs_scored.csv --part2 results/runs_scored.csv --out results_web
```
* Hand-check 20 runs (rescore after a scorer fix; never rerun).
* `grep -rl` your SEC contact address and `sk-ant-` in `runs_web*/`: both must print nothing.
* Write the headline numbers in `notes.txt`.
* Commit the code, the frozen key, the runs and the results yourself.

---

## 10. Revised calendar (the deadline stays Nov 11)

| Date | Part | Work |
|---|---|---|
| Wed Oct 28 | 3 | This design; SEC_USER_AGENT; install Playwright; `answer_key.py` |
| Thu Oct 29 | 3 | Freeze the key; walk STEPS by hand; capture fixtures; mock + selftest pass |
| Fri Oct 30 | 3 | Pilot (≈ $5); read the transcripts; repeat rule; freeze prompts `web-v1` |
| Sat Oct 31 – Sun Nov 1 | 3 | Main run (192 runs, resume-safe, ≤ $100) |
| Mon Nov 2 | 3 | Score; hand-check 20 runs; fix tags only if the hand check shows a scorer bug (rescore, never rerun) |
| Tue Nov 3 | 3 | `analyze_web.py`; Part 2 vs Part 3 table; notes; commit |
| Wed Nov 4 | 4 (old Part 3) | Combined analysis: Part 2 + Part 3 figures, Fisher tests, error-tag story |
| Thu Nov 5 | 4 | Qualitative layer: 6–8 annotated transcripts ("right number, wrong row") |
| Fri Nov 6 – Sat Nov 7 | 4 | Write-up draft (4–6 pages); Part 3 gets its own results section |
| Sun Nov 8 | 4 | Revise the paper; README polish |
| Mon Nov 9 | 4 | 10-minute talk slides (add 2 slides: the click path, and Part 2 vs Part 3) |
| Tue Nov 10 | 4 | Rehearse; portfolio items |
| **Wed Nov 11** | 4 | **Final deadline:** submit paper, repo, talk |

---

## 11. Documents to update alongside this design

* **Guide artifact** (`factor-forge-guide.html`): insert "Part 3: Form Forge" before the current Part 3, renumber that one to **Part 4**, and adopt the calendar in §10.
* `README.md`: project overview, the new part, folder map, and the headline-results placeholder.
* `docs/01` (plain English), `docs/02` (add H1–H5 and the web scoring rules), `docs/03` (add the §9 checklist steps), `docs/04` (add the SEC traps from §2 and §4), `docs/05` (glossary: accession number, 10-Q/10-K, XBRL, R page, FilingSummary.xml, noncontrolling interest, preferred stock, stockholders' deficit, robots.txt, User-Agent, headless browser, tool use, prompt caching).
* `docs/code/00-how-the-pieces-fit.md` plus new explainers `docs/code/09…15` for each `web/*.py`.
* `docs/class-update.md` and `docs/class-script.md`: one paragraph and one slide on why Part 3 exists (the ceiling at 316/320).
* `.env.example`: the `SEC_USER_AGENT` placeholder. `notes.txt`: dated entry for the design decision and the Fed DDP removal notice.

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| SEC returns 403 to the harness (UA missing, too fast) | Declared UA, ≤ 5 req/s, sequential runs, asset cache. If it persists: fall back to the NY Fed SOFR family (§1) and log it |
| The live site changes mid-run (new filings appear) | The tasks target fixed past filings, so the answers can't change, only the distractors. Repeat-major order spreads any change evenly across models |
| The EDGAR UI labels differ from the STEPS text | Hand walk + fixture capture on Oct 29, before the pilot |
| Cost overrun | Pilot-measured repeat rule + `--budget-usd 100` |
| A model "solves" it from memory | Post-cutoff filings, plus the `UNGROUNDED` tag |
| The model knows URL patterns and skips the search form | Allowed but measured (`visited_search_form`). The accession can't be known without the filings table |
| A frames accession differs from the original filing | `answer_key.py` picks the earliest-filed fact for that end date and records the form |

---

## 13. Build status and changes from the first draft (2026-10-28)

Built with Claude Code (infrastructure only). No Anthropic API calls were made, nothing was committed, `.env` was never read, and all live SEC traffic used the test User-Agent `FactorForge-test admin@example.com` at ≤ 5 requests/s.

**Changes from the first draft**
1. **Netflix (T4) original filing** is 0001065280-26-000212 (filed 2026-07-17). -000291 is the October 10-Q that repeats the number; the scorer calls it `WRONG_FILING`.
2. **`max_tokens` per turn is 16,000**, not 4,000 (thinking counts toward it).
3. **Tag order:** `UNGROUNDED` and `WRONG_ENTITY` now come before `NAV_ERROR`, and there is a `REFUSAL` tag. With the draft's order, guesses and wrong-company answers would all have been `NAV_ERROR`.
4. **Requests go through a plain HTTP client** (§3.1), because SEC answered 403 to headless Chromium's own requests. A test that also tried a browser-style User-Agent was dropped; nothing is disguised.
5. **CDN page libraries** (jQuery, Bootstrap, DataTables) are allowed only as scripts/stylesheets of SEC pages.
6. **Fixtures** live in one shared `web/fixtures/` folder; each run also saves `requests.jsonl`.
7. **Stalls:** about 690 s stalls happened 3 times while loading one SEC script (root cause unknown). Each request is now capped at 25 s, and a tool call slower than 120 s doesn't count toward the 12 minutes.
8. **9 mock personas** (§3.5), not 7.
9. **T6 preferred** is tagged under a different XBRL name for JPM; `answer_key.py` tries fallback names.

**Real test outputs**
```
answer_key.py --check     sha256 OK for 11 raw files ... frozen key matches a rebuild from raw files: True
capture_fixtures.py       T1: matches the key; 41 network requests; max 5 requests in any 1 s window
                          T4: matches the key; 39 network requests; max 4 requests in any 1 s window
                          fixtures: 69 saved responses
run_web.py --dry-run      18 runs (T1, T4 x 9 personas, live site); after fixes every persona answered as planted
score_web.py              scored 18 runs: PASS 4, WRONG_PERIOD 2, GAVE_UP 2, UNGROUNDED 2, STEP_LIMIT 2, UNITS 2,
                          WRONG_ENTITY 2, WRONG_LINE 2 -- 0 mismatches
analyze_web.py            overall 4/18 22.2% [9.0, 45.2]; wrote summary.md, 5 CSVs and 3 figures
selftest_web.py           148/148 checks passed / ALL CHECKS PASSED
```

**Still open before the pilot**
* Only T1 and T4 were walked live. The labels for T2, T3, T5–T8 in `tasks_web.json` and `mock_agent.py` are unverified, and `PROMPT_VERSION` is still `"web-v1-draft"`. Run `capture_fixtures.py --all` (§9 Step 3).
* Shortcuts left open: the filing's XBRL instance file (`*_htm.xml`) and the inline viewer (`/ix?doc=`) are inside the filing folder and allowed. The Interactive Data viewer is under `/cgi-bin` and blocked by robots.txt. `visited_search_form` only measures whether the form was used.
* The key was frozen with the test User-Agent; refetch with `answer_key.py --force` if you want it under your own.
* The student should confirm the HTTP-client approach (change 4) before the paid pilot.
