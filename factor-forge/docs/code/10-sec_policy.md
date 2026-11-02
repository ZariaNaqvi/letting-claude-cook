# 10 - `web/sec_policy.py`

## In one sentence

It decides, for every request the browser makes, whether it is allowed, and makes the allowed ones politely: declared User-Agent, at most 5 per second, SEC's robots.txt obeyed.

## Why it exists

Two jobs:
1. **Force the models through the web pages.** The answer key's source, `data.sec.gov/api/xbrl`, is blocked, so a model can't just ask the API.
2. **Follow SEC's fair-access rules.** SEC asks robots to declare who they are and to stay under 10 requests per second. Its robots.txt forbids `/cgi-bin` and a few other paths.

## How to try it

```bash
python web/sec_policy.py https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json https://www.sec.gov/edgar/browse/?CIK=320193
```

It prints each URL and `(allowed, reason)`, e.g. `(False, 'XBRL API is blocked in this experiment (collect data through the EDGAR web pages)')`. No network.

## The rules (`classify`)

| URL | Decision |
|---|---|
| `data.sec.gov/api/xbrl/*` | blocked: the answer key |
| `data.sec.gov/submissions/*` | allowed: the filings list the company page loads |
| other `data.sec.gov` | blocked |
| `efts.sec.gov` | allowed: the search and autocomplete service |
| `www.sec.gov`, `sec.gov` | allowed unless robots.txt disallows it (`/cgi-bin`, `/search/`, `/Archives/bin`, ...; `/Archives/edgar/data` is allowed) |
| jQuery/Bootstrap/DataTables CDNs | allowed **only** as a script or stylesheet of a page |
| anything else | blocked |

`ROBOTS_RULES` is a copy of SEC's robots.txt from Oct 28. `robots_allowed` uses the usual rule: the longest matching pattern wins, and Allow wins a tie.

## The User-Agent (`load_user_agent`)

It reads `SEC_USER_AGENT` from the environment, else only that line of `factor-forge/.env`. It stops with an error if the value is missing, still `Your Name your.address@example.edu`, has no `@`, or is the test value `FactorForge-test admin@example.com` in a paid run. `ua_digest` gives its sha256, which is all that run files store.

## The rate limiter (`RateLimiter`)

One shared token bucket: each request waits until 0.2 s after the previous one. So at most 5 per second, across pages, scripts, JSON and redirect hops. `max_in_window` counts the busiest 1-second window (the self-test and `capture_fixtures.py` print it).

## The route handler (`Policy.handle`)

Every request from Chromium arrives here. In order:
1. not allowed → abort, log `BLOCK <reason>`; a blocked page navigation is remembered so the tool can say `BLOCKED: ...`
2. image, media or font → abort (`skip`)
3. **offline** mode → serve from `web/fixtures/`, or a 404 `OFFLINE: page not in fixtures`
4. a cached `.js`/`.css` → serve from `web/.asset_cache/`
5. otherwise → fetch it with `httpx2`, which sends **only** the declared User-Agent, follows up to 5 redirects itself (each one re-checked with `classify`), and gives up after 25 s. Chromium then renders the response.

   **Redirected pages.** If a page request was redirected, the handler doesn't hand the body to Chromium under the old URL, because then the model would see the wrong address and relative links would point to the wrong place. It also can't send Chromium a 302: Chromium follows that itself, outside the handler. So the old URL gets a one-line stub (`location.replace(<final URL>)`). The browser then asks for the final URL, which goes through the handler again and is served from the response already fetched, with no second network request. A redirect to a blocked URL is aborted and counted as a blocked page. `doc_status` remembers the HTTP status of each page served, so the observation header shows the final page's status.

A 403 on a page counts in `http_403`; the runner then stops the whole session. Every decision is logged and saved as `requests.jsonl`.

**Why a plain HTTP client?** When Chromium fetched SEC pages itself, SEC answered `403 Undeclared Automated Tool`, even with the declared User-Agent. The same request from a plain client got 200. Nothing is disguised: no browser User-Agent, no extra headers.

## Modes

| mode | used by | network |
|---|---|---|
| `live` | `run_web.py` | yes |
| `record` | `capture_fixtures.py` | yes, and saves every response |
| `offline` | `run_web.py --offline`, the self-test | none |
