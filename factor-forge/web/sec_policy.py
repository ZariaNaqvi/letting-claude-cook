"""
Form Forge -- access policy for the agent's browser (SEC EDGAR only).

Every request the headless browser makes (pages AND sub-resources) passes through
`Policy.handle(route)`, installed with context.route("**/*", ...). The policy:

  1. allows only www.sec.gov (+ sec.gov), efts.sec.gov and data.sec.gov/submissions/*
  2. BLOCKS data.sec.gov/api/xbrl/* -- that API is the answer-key source, so the
     model must use the web pages, not the API
  3. obeys SEC robots.txt (rules copied below, checked 2026-10-28; /cgi-bin is out)
  4. aborts images, media and fonts (saves traffic, the agent reads text only)
  5. rate-limits to <= 5 requests/s across ALL requests (SEC allows 10/s)
  6. serves .js/.css from a local cache after the first download (web/.asset_cache/)
  7. makes every allowed request with a plain HTTP client that sends ONLY the
     declared User-Agent (Chromium renders the result). This keeps the traffic
     exactly what SEC asks automated tools to send.
  8. optional: records every response to a fixture folder (--record) or serves ONLY
     from fixtures (--offline), so the self-test never touches the network

The User-Agent comes from SEC_USER_AGENT (SEC requires a declared contact). The
harness refuses to start without it.

    python web/sec_policy.py https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json
"""
import hashlib
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
ASSET_CACHE = os.path.join(HERE, ".asset_cache")
UA_PLACEHOLDER = "Your Name your.address@example.edu"
TEST_UA = "FactorForge-test admin@example.com"     # for offline tests and the dry run only
MAX_RPS = 5.0
FETCH_DEADLINE_S = 25.0      # wall-clock cap on one HTTP request (redirects included)

# ---------------------------------------------------------------------------
# robots.txt of www.sec.gov, "User-agent: *" group (fetched 2026-10-28).
# Matching follows the usual robots rules: the LONGEST matching pattern wins,
# and Allow wins a tie. '*' = any characters, '$' = end of URL.
# ---------------------------------------------------------------------------
ROBOTS_RULES = [
    ("allow", "/core/*.css$"), ("allow", "/core/*.css?"), ("allow", "/core/*.js$"), ("allow", "/core/*.js?"),
    ("allow", "/profiles/*.css$"), ("allow", "/profiles/*.css?"), ("allow", "/profiles/*.js$"),
    ("allow", "/profiles/*.js?"),
    ("disallow", "/core/"), ("disallow", "/profiles/"),
    ("disallow", "/README.md"), ("disallow", "/admin/"), ("disallow", "/comment/reply/"),
    ("disallow", "/filter/tips"), ("disallow", "/node/add/"), ("disallow", "/search/"),
    ("disallow", "/search?"), ("disallow", "/user/register"), ("disallow", "/user/password"),
    ("disallow", "/user/login"), ("disallow", "/user/logout"), ("disallow", "/media/oembed"),
    ("disallow", "/*/media/oembed"), ("disallow", "/index.php/"),
    ("allow", "/Archives/edgar/data"),
    ("disallow", "/Archives/bin"), ("disallow", "/Archives/etc"), ("disallow", "/Archives/usr"),
    ("disallow", "/cgi-bin"), ("disallow", "/bin"), ("disallow", "/Archives/edgar/vprr/XXXX"),
    ("disallow", "/Archives/edgar/vprr/vprr_removal"), ("disallow", "/Archives/edgar/vprr/bin"),
    ("disallow", "/nb"), ("disallow", "/video/live"), ("disallow", "/node"),
    ("disallow", "/spotlight/equity-market-structure-advisory-committee.shtml"),
]


def _robots_regex(pattern):
    rx = "".join(".*" if ch == "*" else ("$" if ch == "$" else re.escape(ch)) for ch in pattern)
    return re.compile("^" + rx)


_ROBOTS = [(kind, len(p), _robots_regex(p)) for kind, p in ROBOTS_RULES]


def robots_allowed(path_and_query):
    best = None   # (length, kind)
    for kind, n, rx in _ROBOTS:
        if rx.match(path_and_query) and (best is None or n > best[0] or (n == best[0] and kind == "allow")):
            best = (n, kind)
    return best is None or best[1] == "allow"


SEC_HOSTS = {"www.sec.gov", "sec.gov"}
# Public code libraries that EDGAR pages load (jQuery, Bootstrap, DataTables). They are
# allowed ONLY as scripts/stylesheets of an SEC page, never as pages the model can open,
# and are cached after the first download.
LIB_HOSTS = {"code.jquery.com", "cdnjs.cloudflare.com", "stackpath.bootstrapcdn.com",
             "cdn.datatables.net", "cdn.jsdelivr.net"}
LIB_TYPES = {"script", "stylesheet"}


def classify(url):
    """Return (allowed: bool, reason: str) for one URL. Pure function, no network."""
    try:
        u = urlsplit(url)
    except ValueError:
        return False, "unparseable URL"
    if u.scheme in ("data", "blob", "about"):
        return True, "local"
    if u.scheme not in ("http", "https"):
        return False, f"scheme {u.scheme} not allowed"
    host = (u.hostname or "").lower()
    path = u.path or "/"
    pq = path + ("?" + u.query if u.query else "")
    if host == "data.sec.gov":
        if path.startswith("/api/xbrl"):
            return False, "XBRL API is blocked in this experiment (collect data through the EDGAR web pages)"
        if path.startswith("/submissions/"):
            return True, "data.sec.gov submissions (filings list for the browse page)"
        return False, "data.sec.gov path not allowed"
    if host == "efts.sec.gov":
        return True, "EDGAR search service"
    if host in SEC_HOSTS:
        if not robots_allowed(pq):
            return False, "disallowed by www.sec.gov/robots.txt"
        return True, "www.sec.gov"
    return False, f"host {host} is not part of SEC EDGAR"


# ---------------------------------------------------------------------------
# User-Agent
# ---------------------------------------------------------------------------
def load_user_agent(allow_test=False, env_path=None):
    """SEC_USER_AGENT from the environment, else from factor-forge/.env.

    Only the SEC_USER_AGENT line of .env is used. Raises SystemExit if it is
    missing or still the placeholder (SEC blocks anonymous robots).
    """
    ua = os.environ.get("SEC_USER_AGENT", "").strip().strip('"')
    if not ua:
        env = env_path or os.environ.get("FF_ENV_FILE") or os.path.join(PROJECT, ".env")
        if os.path.exists(env):
            from dotenv import dotenv_values
            ua = (dotenv_values(env).get("SEC_USER_AGENT") or "").strip().strip('"')
    if not ua or ua == UA_PLACEHOLDER or "@" not in ua or len(ua.split()) < 2:
        raise SystemExit("SEC_USER_AGENT is missing or still the placeholder. Add a line like\n"
                         '  SEC_USER_AGENT="Firstname Lastname contact@yourdomain"\n'
                         "to factor-forge/.env (SEC requires a declared User-Agent).")
    if ua == TEST_UA and not allow_test:
        raise SystemExit("SEC_USER_AGENT is the test value; set your own for real runs.")
    return ua


def ua_digest(ua):
    return hashlib.sha256(ua.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Rate limiter: global token bucket shared by every request
# ---------------------------------------------------------------------------
class RateLimiter:
    def __init__(self, rps=MAX_RPS, burst=1):
        self.interval = 1.0 / rps
        self.lock = threading.Lock()
        self.next_t = 0.0
        self.stamps = []          # monotonic times of granted requests (for the self-test)

    def acquire(self):
        with self.lock:
            now = time.monotonic()
            wait = self.next_t - now
            if wait > 0:
                time.sleep(wait)
                now = time.monotonic()
            self.next_t = max(now, self.next_t) + self.interval
            self.stamps.append(now)
            if len(self.stamps) > 5000:
                self.stamps = self.stamps[-1000:]

    def max_in_window(self, window=1.0):
        s, best, j = self.stamps, 0, 0
        for i in range(len(s)):
            while s[i] - s[j] >= window:
                j += 1
            best = max(best, i - j + 1)
        return best


# ---------------------------------------------------------------------------
# Fixtures (record / offline replay)
# ---------------------------------------------------------------------------
def _key(method, url):
    return hashlib.sha256(f"{method} {url}".encode()).hexdigest()[:24]


class FixtureStore:
    def __init__(self, folder):
        self.folder = folder
        self.index_path = os.path.join(folder, "index.json")
        self.index = json.load(open(self.index_path)) if os.path.exists(self.index_path) else {}

    def get(self, method, url):
        e = self.index.get(_key(method, url))
        if not e:
            return None
        with open(os.path.join(self.folder, e["file"]), "rb") as fh:
            return e, fh.read()

    def put(self, method, url, status, content_type, body, location=None):
        os.makedirs(self.folder, exist_ok=True)
        k = _key(method, url)
        fname = k + ".bin"
        with open(os.path.join(self.folder, fname), "wb") as fh:
            fh.write(body)
        self.index[k] = dict(method=method, url=url, status=status, content_type=content_type,
                             file=fname, sha256=hashlib.sha256(body).hexdigest(), bytes=len(body),
                             location=location)
        with open(self.index_path + ".tmp", "w") as fh:
            json.dump(self.index, fh, indent=1)
        os.replace(self.index_path + ".tmp", self.index_path)


# ---------------------------------------------------------------------------
# The route handler
# ---------------------------------------------------------------------------
SKIP_TYPES = {"image", "media", "font"}


class Policy:
    """One per browser context. mode = 'live' | 'record' | 'offline'."""

    def __init__(self, limiter, user_agent, mode="live", fixtures=None, asset_cache=ASSET_CACHE):
        assert mode in ("live", "record", "offline")
        if mode != "live":
            assert fixtures is not None, "record/offline need a fixture folder"
        self.limiter, self.mode = limiter, mode
        self.store = FixtureStore(fixtures) if fixtures else None
        self.asset_cache = asset_cache
        self.log = []                 # (time, url, resource_type, decision)
        self.blocked_docs = []        # blocked page navigations (document requests)
        self.n_network = 0
        self.offline_misses = []
        self.http_403 = 0
        self.fetch_errors = 0
        self.http = None
        self._pool = ThreadPoolExecutor(max_workers=4)
        if mode != "offline":
            import httpx2   # installed with anthropic; verifies TLS with the system store
            # Redirects are followed HERE: a redirect handed back to Chromium would be fetched by
            # Chromium itself, outside this handler (Playwright does not re-route redirects).
            self.http = httpx2.Client(headers={"User-Agent": user_agent}, timeout=20.0,
                                      follow_redirects=True, max_redirects=5,
                                      event_hooks={"request": [self._on_http_request]})

    def _on_http_request(self, request):
        """Every real HTTP request (redirect hops included) waits for the rate limiter."""
        self.limiter.acquire()
        self.n_network += 1

    def close(self):
        self._pool.shutdown(wait=False, cancel_futures=True)
        if self.http is not None:
            self.http.close()

    # -- helpers ---------------------------------------------------------
    def _asset_path(self, url):
        return os.path.join(self.asset_cache, hashlib.sha256(url.encode()).hexdigest()[:32])

    @staticmethod
    def _is_asset(url, rtype):
        u = urlsplit(url)
        if rtype not in LIB_TYPES:
            return False
        if u.hostname in LIB_HOSTS:
            return True
        return u.hostname in SEC_HOSTS and (u.path.endswith(".js") or u.path.endswith(".css"))

    def _note(self, url, rtype, decision):
        self.log.append((round(time.time(), 3), url[:300], rtype, decision))

    # -- the handler -----------------------------------------------------
    def handle(self, route):
        req = route.request
        url, rtype, method = req.url, req.resource_type, req.method
        ok, reason = classify(url)
        if not ok and rtype in LIB_TYPES and (urlsplit(url).hostname or "") in LIB_HOSTS:
            ok, reason = True, "page library"
        if not ok:
            self._note(url, rtype, "BLOCK " + reason)
            if rtype == "document":
                self.blocked_docs.append((url, reason))
            return route.abort("blockedbyclient")
        if rtype in SKIP_TYPES:
            self._note(url, rtype, "skip")
            return route.abort("blockedbyclient")
        if url.startswith(("data:", "blob:", "about:")):
            return route.continue_()

        # offline replay: serve only what was recorded
        if self.mode == "offline":
            hit = self.store.get(method, url)
            if hit is None:
                self.offline_misses.append(url)
                self._note(url, rtype, "offline-miss")
                return route.fulfill(status=404, content_type="text/plain",
                                     body="OFFLINE: page not in fixtures")
            e, body = hit
            self._note(url, rtype, "fixture")
            headers = {"content-type": e["content_type"]}
            if e.get("location"):
                headers["location"] = e["location"]
            return route.fulfill(status=e["status"], headers=headers, body=body)

        # static asset cache (js/css only; page HTML is always live)
        if self._is_asset(url, rtype):
            p = self._asset_path(url)
            if os.path.exists(p) and os.path.exists(p + ".type"):
                body = open(p, "rb").read()
                ctype = open(p + ".type").read()
                if self.mode == "record":
                    self.store.put(method, url, 200, ctype, body)
                self._note(url, rtype, "asset-cache")
                return route.fulfill(status=200, content_type=ctype, body=body)

        # live / record: the request is made by a plain HTTP client that sends the
        # declared User-Agent (SEC's fair-access rule for automated tools); Chromium
        # only renders what comes back. Redirects are passed back to the browser.
        fwd = {k: v for k, v in req.headers.items() if k.lower() in ("content-type",)}
        t_start = time.time()
        # hard wall-clock deadline per request: httpx's timeouts are per read, so a slowly
        # trickling response could otherwise block the browser for minutes
        fut = self._pool.submit(self.http.request, method, url, headers=fwd, content=req.post_data_buffer)
        try:
            resp = fut.result(timeout=FETCH_DEADLINE_S)
        except Exception as e:  # noqa: BLE001
            self._note(url, rtype, f"fetch-error {type(e).__name__} after {time.time() - t_start:.1f}s")
            if rtype == "document":
                self.fetch_errors += 1
            return route.abort("timedout" if isinstance(e, TimeoutError) else "failed")
        body = resp.content
        ctype = resp.headers.get("content-type", "application/octet-stream")
        loc = None
        if str(resp.url) != url:                    # followed a redirect; must still be an allowed URL
            ok2, why2 = classify(str(resp.url))
            if not ok2:
                self._note(str(resp.url), rtype, "BLOCK after redirect " + why2)
                return route.abort("blockedbyclient")
        if self.mode == "record":
            self.store.put(method, url, resp.status_code, ctype, body, loc)
        if self._is_asset(url, rtype) and resp.status_code == 200:
            os.makedirs(self.asset_cache, exist_ok=True)
            with open(self._asset_path(url), "wb") as fh:
                fh.write(body)
            with open(self._asset_path(url) + ".type", "w") as fh:
                fh.write(ctype)
        if resp.status_code == 403 and rtype == "document":
            self.http_403 += 1
        self._note(url, rtype, f"net {resp.status_code} {time.time() - t_start:.1f}s")
        headers = {"content-type": ctype}
        if loc:
            headers["location"] = loc
        return route.fulfill(status=resp.status_code, headers=headers, body=body)


if __name__ == "__main__":
    for u in sys.argv[1:]:
        print(u, "->", classify(u))
