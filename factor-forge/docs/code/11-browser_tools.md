# 11 - `web/browser_tools.py`

## In one sentence

It runs a headless Chromium browser and turns each page into plain text with clickable refs, so a model can browse with 9 simple tools.

## Why it exists

A model can't see a screen. It needs the page as text, a way to say "click that link", and observations short enough to fit many steps into one conversation. Every model gets the same tools and the same view.

## How to try it

```bash
SEC_USER_AGENT="FactorForge-test admin@example.com" python web/browser_tools.py \
    https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/R4.htm
```

About 10 live requests. It prints the observation and the number of network requests.

## What an observation looks like

```
URL: https://www.sec.gov/... | TITLE: ... | chunk 1/3

[e3 textbox "Name, ticker symbol, or CIK" value=""] ...
[e12 link] 10-Q ...
[chunk 1/3; call read_page(page=2) for more]
```

- `SNAPSHOT_JS` marks every visible link, button, input, select, textarea and ARIA role element with `data-ff-ref="eN"` and puts `[eN kind "label"]` into the page text where it appears. Text boxes show their value; selects show up to 25 options.
- Refs stay the same while the page stays the same; after a navigation they are renumbered.
- The text is cut into chunks of 10,000 characters (about 2,500 tokens). One tool result is capped at 10,800 characters.

## The 9 tools (`TOOL_SCHEMAS` + `submit_tool`)

| tool | does |
|---|---|
| `goto(url)` | Opens a URL (checked by `sec_policy.classify` first). Blocked → `BLOCKED: <url> -- <reason>` |
| `read_page(page)` | Re-reads the page; chunk `page` |
| `find_text(query)` | Up to 20 matching lines (case-insensitive) with 1 line of context and the chunk number |
| `click(ref)` | Clicks; a link that opens a new tab is opened in the same tab |
| `fill(ref, text)` | Types into a text box and reports suggestions (the company autocomplete) |
| `select_option(ref, value)` | Chooses a `<select>` option |
| `press(key)` | `Enter`, `Tab`, `Escape`, `ArrowDown`, `ArrowUp` |
| `back()` | Browser back |
| `submit_answer(...)` | Ends the run. Schema from `tasks_web.json` plus `give_up` and `evidence_url` |

An unknown ref returns `ERROR: unknown ref eN, call read_page`.

## The session (`BrowserSession`)

- A **fresh browser context** for each run: no cookies or history from other runs. Viewport 1280×1600.
- Every request goes through `sec_policy.Policy.handle`.
- Page loads wait for `domcontentloaded` (20 s), then up to 20 s for `networkidle`, then 0.6 s more so the JavaScript filings table can render. One retry. Two failed tries count as a `site_error`.
- It records every URL shown (`visited`), every observation (`pages_seen`), `blocked_attempts` and `site_errors`. The scorer uses these.

## Things to check

- If a page looks empty in a pilot transcript, the JS table may need longer than `SETTLE_MS`. Fix it before the main run and write it in `notes.txt`.
