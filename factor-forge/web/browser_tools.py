"""
Form Forge -- the browser the model drives (Playwright, headless Chromium).

The model never sees HTML. Each tool returns an OBSERVATION: the page's rendered,
visible text, with every clickable or typeable element marked inline by a ref,
for example

    [e12 link] 10-Q          [e3 textbox "Company name or ticker" value=""]

The model acts by ref: click(ref="e12"), fill(ref="e3", text="Apple Inc").
Refs stay the same while the page stays the same; after a navigation they are
renumbered. Long pages are cut into chunks of <= 10,000 characters (~2,500
tokens); read_page(page=n) shows chunk n and find_text(query) searches all of them.

Tools (identical for every model): goto, read_page, find_text, click, fill,
select_option, press, back, submit_answer. TOOL_SCHEMAS below are the exact JSON
schemas sent to the API; submit_answer's input schema comes from tasks_web.json.

Try it (live site, ~10 requests):
    SEC_USER_AGENT="FactorForge-test admin@example.com" python web/browser_tools.py \
        https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/R4.htm
"""
import os
import sys
import time

import sec_policy

CHUNK_CHARS = 10_000          # ~2,500 tokens per observation chunk
MAX_OBS_CHARS = 10_800        # hard cap on one tool result (chunk + header + footer)
LOAD_TIMEOUT_MS = 20_000
SETTLE_MS = 600               # extra wait after load for JS tables to render
VIEWPORT = {"width": 1280, "height": 1600}

# ---------------------------------------------------------------------------
# JS run in the page: give interactive elements refs and return the text with
# inline [eN kind "label"] markers. Markers are inserted as temporary <span>s so
# body.innerText (= what a person sees, CSS-hidden text excluded) includes them
# at the right place, then removed again.
# ---------------------------------------------------------------------------
SNAPSHOT_JS = r"""
() => {
  const SEL = 'a[href], button, input:not([type=hidden]), select, textarea, [role=button], [role=link], [role=tab], [role=option], summary';
  if (!window.__ffNext) window.__ffNext = 1;
  const vis = el => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return false;
    const s = getComputedStyle(el);
    return s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
  };
  const label = el => {
    let t = el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.getAttribute('title') || '';
    if (!t && el.id) { const l = document.querySelector('label[for="' + CSS.escape(el.id) + '"]'); if (l) t = l.innerText; }
    if (!t && (el.tagName === 'INPUT') && (el.type === 'submit' || el.type === 'button')) t = el.value;
    return (t || '').replace(/\s+/g, ' ').trim().slice(0, 60);
  };
  const kind = el => {
    const tag = el.tagName.toLowerCase(), role = el.getAttribute('role');
    if (role) return role;
    if (tag === 'a') return 'link';
    if (tag === 'select') return 'select';
    if (tag === 'textarea') return 'textbox';
    if (tag === 'input') {
      const t = (el.type || 'text').toLowerCase();
      if (['submit', 'button', 'reset', 'image'].includes(t)) return 'button';
      if (t === 'checkbox' || t === 'radio') return t;
      return 'textbox';
    }
    return tag;
  };
  const els = [], spans = [];
  for (const el of document.querySelectorAll(SEL)) {
    if (!vis(el)) continue;
    if ((el.getAttribute('onclick') || '').includes('showAR')) continue;   // R-page definition pop-ups
    if (!el.dataset.ffRef) el.dataset.ffRef = 'e' + (window.__ffNext++);
    const k = kind(el);
    let m = el.dataset.ffRef + ' ' + k;
    const lab = label(el);
    const ownText = (el.innerText || '').trim();
    if (lab && lab !== ownText) m += ' "' + lab + '"';
    if (k === 'textbox') m += ' value="' + (el.value || '').slice(0, 80) + '"';
    if (k === 'checkbox' || k === 'radio') m += el.checked ? ' checked' : ' unchecked';
    if (k === 'select') {
      const opts = Array.from(el.options).slice(0, 25).map(o => o.value === o.text ? o.text : o.value + '=' + o.text);
      m += ' value="' + el.value + '" options=[' + opts.join(' | ') + (el.options.length > 25 ? ' | ...' : '') + ']';
    }
    if (el.tagName === 'A') {
      const h = el.getAttribute('href') || '';
      if (h.startsWith('javascript')) m += ' (script)';
    }
    els.push({ref: el.dataset.ffRef, kind: k, label: lab, text: ownText.slice(0, 80),
               href: el.tagName === 'A' ? el.href : null, target: el.getAttribute('target')});
    const sp = document.createElement('span');
    sp.textContent = '[' + m + '] ';
    sp.setAttribute('data-ff-marker', '1');
    sp.style.textTransform = 'none';
    if (k === 'select' || k === 'textbox') { el.parentNode.insertBefore(sp, el); }
    else if (el.firstChild) { el.insertBefore(sp, el.firstChild); }
    else { el.parentNode.insertBefore(sp, el); }
    spans.push(sp);
  }
  // Text of the page; XML files shown by Chromium's viewer have no <body> text styles
  let text = document.body ? document.body.innerText : document.documentElement.textContent;
  for (const sp of spans) sp.remove();
  return {text: text || '', elements: els, title: document.title || ''};
}
"""


# ---------------------------------------------------------------------------
# Tool schemas (sent to the API; identical for every model and condition)
# ---------------------------------------------------------------------------
def _tool(name, desc, props, required):
    return {"name": name, "description": desc,
            "input_schema": {"type": "object", "properties": props, "required": required,
                             "additionalProperties": False}}


TOOL_SCHEMAS = [
    _tool("goto", "Open a URL in the browser (like typing it in the address bar). Returns the first chunk of "
          "the rendered page. Only SEC EDGAR pages can be opened; others return BLOCKED.",
          {"url": {"type": "string", "description": "Absolute https URL"}}, ["url"]),
    _tool("read_page", "Re-read the current page (it may have changed after scripts ran). Long pages are split "
          "into chunks; pass page=2, 3, ... to see later chunks.",
          {"page": {"type": "integer", "minimum": 1, "description": "Chunk number, default 1"}}, []),
    _tool("find_text", "Search the whole current page (all chunks) for a word or phrase, case-insensitive. Returns "
          "up to 20 matching lines with one line of context and the chunk number of each.",
          {"query": {"type": "string"}}, ["query"]),
    _tool("click", "Click an element by its ref from the latest observation, e.g. e12. Returns the page after "
          "the click.", {"ref": {"type": "string"}}, ["ref"]),
    _tool("fill", "Type text into a textbox (replacing what is there). Returns a short confirmation and any "
          "suggestions that appeared (for example a company-name autocomplete list).",
          {"ref": {"type": "string"}, "text": {"type": "string"}}, ["ref", "text"]),
    _tool("select_option", "Choose an option of a <select> element by its value or visible text.",
          {"ref": {"type": "string"}, "value": {"type": "string"}}, ["ref", "value"]),
    _tool("press", "Press a key in the focused element.",
          {"key": {"type": "string", "enum": ["Enter", "Tab", "Escape", "ArrowDown", "ArrowUp"]}}, ["key"]),
    _tool("back", "Go back to the previous page.", {}, []),
]


def submit_tool(answer_schema):
    """The submit_answer tool for one task (its schema comes from tasks_web.json)."""
    props = dict(answer_schema["properties"])
    props["give_up"] = {"type": "boolean", "description": "true if you could not find the answer"}
    props["evidence_url"] = {"type": "string", "description": "URL of the page that shows the number"}
    return _tool("submit_answer", "Submit your final answer. This ends the task. If you cannot find the answer, "
                 "call it with give_up=true (other fields may then be empty).", props, [])


# ---------------------------------------------------------------------------
# The browser session
# ---------------------------------------------------------------------------
class BrowserSession:
    """One fresh Chromium context per run (no cookies, no history from other runs)."""

    def __init__(self, user_agent, mode="live", fixtures=None, limiter=None, headless=True):
        from playwright.sync_api import sync_playwright
        self.limiter = limiter or sec_policy.RateLimiter()
        self.policy = sec_policy.Policy(self.limiter, user_agent, mode=mode, fixtures=fixtures)
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=headless)
        self.context = self.browser.new_context(user_agent=user_agent, viewport=VIEWPORT,
                                                java_script_enabled=True, locale="en-US")
        self.context.route("**/*", self.policy.handle)
        self.page = self.context.new_page()
        self.context.on("page", self._on_new_page)
        self.visited = []          # every main-frame URL the browser showed
        self.page.on("framenavigated", self._on_nav)
        self.chunks, self.elements, self.title = [""], {}, ""
        self.last_status = None
        self.blocked_attempts = 0
        self.site_errors = 0
        self.pages_seen = []       # observation texts (for grounding checks)
        self._popup = None

    # -- events ----------------------------------------------------------
    def _on_nav(self, frame):
        if frame == frame.page.main_frame:
            self.visited.append(frame.url)

    def _on_new_page(self, new_page):
        # a link that opens a new tab: remember its URL; click() then opens it in the same tab
        self._popup = new_page

    def close(self):
        for f in (self.context.close, self.browser.close, self._pw.stop, self.policy.close):
            try:
                f()
            except Exception:  # noqa: BLE001
                pass

    # -- internals -------------------------------------------------------
    def _settle(self):
        try:
            self.page.wait_for_load_state("networkidle", timeout=LOAD_TIMEOUT_MS)
        except Exception:  # noqa: BLE001 -- some pages never go idle; use what is there
            pass
        self.page.wait_for_timeout(SETTLE_MS)

    def _load(self, url):
        """page.goto with one retry. Returns (status or None, error or None)."""
        err = None
        for attempt in range(2):
            try:
                resp = self.page.goto(url, wait_until="domcontentloaded", timeout=LOAD_TIMEOUT_MS)
                self._settle()
                self.last_status = resp.status if resp else None
                return self.last_status, None
            except Exception as e:  # noqa: BLE001
                err = f"{type(e).__name__}: {str(e).splitlines()[0][:160]}"
                if "ERR_BLOCKED_BY_CLIENT" in str(e):
                    return None, "BLOCKED"
                time.sleep(2)
        self.site_errors += 1
        return None, err

    def snapshot(self):
        """Refresh text + refs of the current page and split it into chunks."""
        try:
            snap = self.page.evaluate(SNAPSHOT_JS)
        except Exception as e:  # noqa: BLE001 -- e.g. navigation in progress
            self.page.wait_for_timeout(800)
            try:
                snap = self.page.evaluate(SNAPSHOT_JS)
            except Exception:  # noqa: BLE001
                snap = {"text": f"(page could not be read: {type(e).__name__})", "elements": [], "title": ""}
        self.title = snap["title"]
        self.elements = {e["ref"]: e for e in snap["elements"]}
        lines = [ln.rstrip() for ln in snap["text"].replace("\r", "").split("\n")]
        text = "\n".join(ln for i, ln in enumerate(lines) if ln or (i and lines[i - 1]))  # squeeze blank runs
        self.chunks = _split(text, CHUNK_CHARS) or [""]
        return self.chunks

    def observe(self, page=1, note=None):
        n = len(self.chunks)
        page = max(1, min(int(page or 1), n))
        head = f"URL: {self.page.url} | TITLE: {self.title[:100]} | chunk {page}/{n}"
        if self.last_status and self.last_status >= 400:
            head += f" | HTTP {self.last_status}"
        body = self.chunks[page - 1]
        foot = f"\n[chunk {page}/{n}; call read_page(page={page + 1}) for more]" if page < n else ""
        obs = (note + "\n" if note else "") + head + "\n\n" + body + foot
        obs = obs[:MAX_OBS_CHARS]
        self.pages_seen.append(obs)
        return obs

    def _blocked(self, url, reason):
        self.blocked_attempts += 1
        msg = f"BLOCKED: {url} -- {reason}"
        self.pages_seen.append(msg)
        return msg

    # -- the tools -------------------------------------------------------
    def goto(self, url):
        ok, reason = sec_policy.classify(url)
        if not ok:
            return self._blocked(url, reason)
        status, err = self._load(url)
        if err == "BLOCKED":
            return self._blocked(url, self.policy.blocked_docs[-1][1] if self.policy.blocked_docs else "blocked")
        if err:
            return f"ERROR: could not load {url} ({err})"
        self.snapshot()
        return self.observe(1)

    def read_page(self, page=1):
        self.snapshot()
        return self.observe(page)

    def find_text(self, query):
        self.snapshot()
        q = (query or "").lower().strip()
        if not q:
            return "ERROR: empty query"
        hits = []
        for ci, chunk in enumerate(self.chunks, 1):
            lines = chunk.split("\n")
            for i, ln in enumerate(lines):
                if q in ln.lower():
                    ctx = lines[max(0, i - 1): i + 2]
                    hits.append(f"(chunk {ci}) " + " / ".join(c.strip() for c in ctx if c.strip())[:400])
        head = f"URL: {self.page.url} | find_text {query!r}: {len(hits)} match(es)"
        out = head + ("\n" + "\n".join(hits[:20]) if hits else "") + \
            ("\n(more matches not shown)" if len(hits) > 20 else "")
        out = out[:MAX_OBS_CHARS]
        self.pages_seen.append(out)
        return out

    def _locate(self, ref):
        if ref not in self.elements:
            return None
        loc = self.page.locator(f'[data-ff-ref="{ref}"]')
        return loc if loc.count() else None

    def click(self, ref):
        loc = self._locate(ref)
        if loc is None:
            return f"ERROR: unknown ref {ref}, call read_page"
        el = self.elements[ref]
        if el.get("href") and not el["href"].startswith("javascript"):
            ok, reason = sec_policy.classify(el["href"])
            if not ok:
                return self._blocked(el["href"], reason)
        before, n_blocked = self.page.url, len(self.policy.blocked_docs)
        err = None
        try:
            loc.first.evaluate("e => e.removeAttribute('target')")
        except Exception:  # noqa: BLE001
            pass
        # A real mouse click first; if the element is covered or still animating (DataTables
        # redraws), fall back to a forced click and then to the DOM click() a script would do.
        for how in ("mouse", "force", "dom"):
            try:
                if how == "mouse":
                    loc.first.click(timeout=6000)
                elif how == "force":
                    loc.first.click(timeout=4000, force=True)
                else:
                    loc.first.evaluate("e => e.click()")
                err = None
                break
            except Exception as e:  # noqa: BLE001
                err = e
                if self.page.url != before:      # the click did navigate, the wait just failed
                    err = None
                    break
        if err is not None:
            return f"ERROR: click failed ({type(err).__name__}: {str(err).splitlines()[0][:120]})"
        self._settle()
        if self._popup is not None:
            pop, self._popup = self._popup, None
            try:
                pop.wait_for_load_state("domcontentloaded", timeout=LOAD_TIMEOUT_MS)
                url = pop.url
                pop.close()
                if url and url != "about:blank":
                    self._load(url)
            except Exception:  # noqa: BLE001
                pass
        if len(self.policy.blocked_docs) > n_blocked and self.page.url == before:
            return self._blocked(*self.policy.blocked_docs[-1])
        self.snapshot()
        return self.observe(1)

    def fill(self, ref, text):
        loc = self._locate(ref)
        if loc is None:
            return f"ERROR: unknown ref {ref}, call read_page"
        old = set(self.elements)
        try:
            loc.first.click(timeout=5000)
            loc.first.fill("", timeout=5000)
            loc.first.press_sequentially(text, delay=40, timeout=15000)   # real keystrokes fire autocomplete
        except Exception as e:  # noqa: BLE001
            return f"ERROR: fill failed ({type(e).__name__}: {str(e).splitlines()[0][:120]})"
        self._settle()
        self.snapshot()
        new = [e for r, e in self.elements.items() if r not in old]
        lines = [f"Typed {text!r} into {ref}. URL: {self.page.url}"]
        if new:
            lines.append("New elements that appeared (e.g. suggestions):")
            lines += [f"[{e['ref']} {e['kind']}] {(e['text'] or e['label'])[:100]}" for e in new[:30]]
        else:
            lines.append("No new elements appeared. Use press(key='Enter') or click a button to submit.")
        out = "\n".join(lines)
        self.pages_seen.append(out)
        return out

    def select_option(self, ref, value):
        loc = self._locate(ref)
        if loc is None:
            return f"ERROR: unknown ref {ref}, call read_page"
        try:
            try:
                loc.first.select_option(value=value, timeout=5000)
            except Exception:  # noqa: BLE001
                loc.first.select_option(label=value, timeout=5000)
        except Exception as e:  # noqa: BLE001
            return f"ERROR: select failed ({type(e).__name__})"
        self._settle()
        self.snapshot()
        return self.observe(1, note=f"Selected {value!r} in {ref}.")

    def press(self, key):
        try:
            self.page.keyboard.press(key)
        except Exception as e:  # noqa: BLE001
            return f"ERROR: press failed ({type(e).__name__})"
        self._settle()
        self.snapshot()
        return self.observe(1)

    def back(self):
        try:
            self.page.go_back(wait_until="domcontentloaded", timeout=LOAD_TIMEOUT_MS)
        except Exception as e:  # noqa: BLE001
            return f"ERROR: back failed ({type(e).__name__})"
        self._settle()
        self.snapshot()
        return self.observe(1)

    def run_tool(self, name, args):
        """Dispatch one tool call. Returns the observation string."""
        args = args or {}
        if name == "goto":
            return self.goto(str(args.get("url", "")))
        if name == "read_page":
            return self.read_page(args.get("page", 1))
        if name == "find_text":
            return self.find_text(str(args.get("query", "")))
        if name == "click":
            return self.click(str(args.get("ref", "")))
        if name == "fill":
            return self.fill(str(args.get("ref", "")), str(args.get("text", "")))
        if name == "select_option":
            return self.select_option(str(args.get("ref", "")), str(args.get("value", "")))
        if name == "press":
            return self.press(str(args.get("key", "Enter")))
        if name == "back":
            return self.back()
        return f"ERROR: unknown tool {name}"


def _split(text, n):
    """Cut text into pieces of <= n chars, at line breaks where possible."""
    out, cur = [], []
    size = 0
    for ln in text.split("\n"):
        while len(ln) > n:                       # a single giant line
            if cur:
                out.append("\n".join(cur))
                cur, size = [], 0
            out.append(ln[:n])
            ln = ln[n:]
        if size + len(ln) + 1 > n and cur:
            out.append("\n".join(cur))
            cur, size = [], 0
        cur.append(ln)
        size += len(ln) + 1
    if cur:
        out.append("\n".join(cur))
    return [c for c in out if c.strip()]


if __name__ == "__main__":
    ua = sec_policy.load_user_agent(allow_test=True)
    b = BrowserSession(ua)
    try:
        for u in sys.argv[1:]:
            print(b.goto(u)[:4000])
            print("... network requests:", b.policy.n_network)
    finally:
        b.close()
