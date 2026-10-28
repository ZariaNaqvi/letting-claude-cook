"""
Form Forge -- fake model for --dry-run (plays the role dryrun_mock.py played in Part 2).

A MockModel has the same interface as the real model in run_web.py: it receives
the conversation (messages) and returns an assistant turn made of tool_use blocks.
It drives the REAL browser (live site, or fixtures with --offline) by reading the
observations it gets back, exactly like a model would -- it finds refs by the text
on the page, reads the accession number off the filing index, opens
FilingSummary.xml, finds the balance-sheet R page and reads the number off it.

Personas (the planted mistake -> the tag the scorer must give):

    good          follows STEPS, reads the right row/column, converts units  -> PASS
    api           first tries data.sec.gov/api/xbrl (BLOCKED), then as good -> PASS, blocked_attempts > 0
    comparative   takes the other date column (prior period)               -> WRONG_PERIOD
    units         submits the number as printed (millions/thousands)       -> UNITS
    wrong_line    takes "Total liabilities and ... equity"                 -> WRONG_LINE
    wrong_entity  does the whole path for a DIFFERENT company              -> WRONG_ENTITY
    hallucinate   answers at step 2 with a made-up number                  -> UNGROUNDED
    give_up       opens the search page, then gives up                     -> GAVE_UP
    loop          keeps re-reading the same page until the step cap        -> STEP_LIMIT

NOTE: this file knows the click path and row names. It is NEVER shown to the
models under test; it is only used with --dry-run.
"""
import re

SEARCH_URL = "https://www.sec.gov/search-filings"
PERSONAS = ["good", "api", "comparative", "units", "wrong_line", "wrong_entity",
            "hallucinate", "give_up", "loop"]
EXPECTED_TAG = {"good": "PASS", "api": "PASS", "comparative": "WRONG_PERIOD", "units": "UNITS",
                "wrong_line": "WRONG_LINE", "wrong_entity": "WRONG_ENTITY", "hallucinate": "UNGROUNDED",
                "give_up": "GAVE_UP", "loop": "STEP_LIMIT"}

# What a careful human reads off each filing: search text, suggestion, form, quarter-end text, row label
FIRMS = {
    "AAPL": dict(cik=320193, search="Apple Inc", suggestion="Apple Inc. (AAPL)", form="10-Q",
                 period="June 27, 2026", row="Total shareholders' equity"),
    "MSFT": dict(cik=789019, search="Microsoft", suggestion="(MSFT)", form="10-K",
                 period="June 30, 2026", row="Total stockholders' equity"),
    "WMT": dict(cik=104169, search="Walmart", suggestion="(WMT)", form="10-Q",
                period="July 31, 2026", row="Total Walmart shareholders' equity"),
    "NFLX": dict(cik=1065280, search="Netflix", suggestion="(NFLX)", form="10-Q",
                 period="June 30, 2026", row="Total stockholders' equity"),
    "DPZ": dict(cik=1286681, search="Domino's Pizza", suggestion="(DPZ)", form="10-Q",
                period="June 14, 2026", row="Total stockholders' deficit"),
    "JPM": dict(cik=19617, search="JPMorgan Chase", suggestion="(JPM)", form="10-Q",
                period="June 30, 2026", row="Total stockholders' equity", minus_row="Preferred stock"),
    "BRK": dict(cik=1067983, search="Berkshire Hathaway Inc", suggestion="BERKSHIRE HATHAWAY INC", form="10-Q",
                period="June 30, 2026", row="Total Berkshire Hathaway shareholders' equity"),
    "KO": dict(cik=21344, search="Coca-Cola", suggestion="(KO)", form="10-Q", period="July 3, 2026",
               row="Equity attributable to shareowners of The Coca-Cola Company"),
    "CVX": dict(cik=93410, search="Chevron", suggestion="(CVX)", form="10-Q", period="June 30, 2026",
                row="Total Chevron Corporation stockholders' equity"),
    "MMM": dict(cik=66740, search="3M", suggestion="(MMM)", form="10-Q", period="June 30, 2026",
                row="Total 3M Company shareholders' equity"),
}
TASK_FIRM = {"T1": "AAPL", "T2": "MSFT", "T3": "WMT", "T4": "NFLX", "T5": "DPZ", "T6": "JPM", "T7": "BRK"}
DECOY = {"T1": "NFLX", "T2": "AAPL", "T3": "AAPL", "T4": "AAPL", "T5": "NFLX", "T6": "AAPL", "T7": "NFLX"}

REF = re.compile(r"\[(e\d+) [^\]]*\]")
NUM = re.compile(r"^\(?-?\$?\s*[\d,]+(\.\d+)?\)?$")


class MockGaveUp(Exception):
    pass


# ---------------------------------------------------------------------------
# Reading observations
# ---------------------------------------------------------------------------
def norm(s):
    return " ".join((s or "").replace("’", "'").replace("\xa0", " ").split()).lower()


def strip_refs(line):
    return REF.sub("", line).strip()


def ref_on_line(obs, text, after=None):
    """First ref on the first line containing `text` (optionally on a line after one containing `after`)."""
    lines = obs.split("\n")
    start = 0
    if after:
        start = next((i for i, ln in enumerate(lines) if norm(after) in norm(ln)), None)
        if start is None:
            return None
    for ln in lines[start:]:
        if norm(text) in norm(ln):
            m = REF.search(ln)
            if m:
                return m.group(1)
    return None


def url_of(obs):
    m = re.match(r"URL: (\S+)", obs)
    return m.group(1) if m else ""


def parse_number(cell):
    c = cell.replace("$", "").replace(",", "").replace(" ", "").strip()
    neg = c.startswith("(") and c.endswith(")")
    c = c.strip("()")
    if not c or not re.match(r"^-?\d+(\.\d+)?$", c):
        return None
    v = float(c)
    return -v if neg else v


def parse_r_page(obs):
    """Return (scale, [column dates], {row label (normalized): [values]}) from an R page observation."""
    lines = [strip_refs(ln) for ln in obs.split("\n")]
    scale = 1
    for ln in lines[:12]:
        if "in millions" in ln.lower():
            scale = 1_000_000
        elif "in thousands" in ln.lower():
            scale = 1_000
        elif "in billions" in ln.lower():
            scale = 1_000_000_000
    dates = [ln.strip() for ln in lines[:40] if re.match(r"^[A-Z][a-z]{2}\.? \d{1,2}, \d{4}$", ln.strip())]
    rows = {}
    for ln in lines:
        if "\t" not in ln:
            continue
        cells = [c.strip() for c in ln.split("\t")]
        vals = [parse_number(c) for c in cells[1:] if c]
        if vals and all(v is not None for v in vals):
            rows.setdefault(norm(cells[0]), vals)
    return scale, dates, rows


def find_row(rows, label):
    want = norm(label)
    for k, v in rows.items():
        if k == want:
            return v
    for k, v in rows.items():
        if k.startswith(want):
            return v
    return None


# ---------------------------------------------------------------------------
# Scripted click paths (generators: yield (tool, args), receive the observation)
# ---------------------------------------------------------------------------
def firm_path(firm, read):
    """Click through EDGAR for one firm. Yields tool calls; returns dict with the numbers it read.

    read = which row/column/unit handling to use: dict(row=..., column='target'|'other', scale=True|False)
    """
    obs = yield ("goto", {"url": SEARCH_URL})
    box = ref_on_line(obs, 'textbox "Name, ticker symbol, or CIK"')
    if not box:
        raise MockGaveUp("no company search box")
    obs = yield ("fill", {"ref": box, "text": firm["search"]})
    sug = ref_on_line(obs, firm["suggestion"])
    if not sug:
        raise MockGaveUp("no suggestion " + firm["suggestion"])
    obs = yield ("click", {"ref": sug})
    exp = ref_on_line(obs, "10-K (annual reports) and 10-Q")
    if not exp:
        raise MockGaveUp("no 10-K/10-Q section")
    obs = yield ("click", {"ref": exp})
    kind = "Quarterly report for quarter ending" if firm["form"] == "10-Q" else "Annual report for year ending"
    filing = ref_on_line(obs, "Filing", after=f"{firm['form']}: {kind} {firm['period']}")
    if not filing:
        obs = yield ("find_text", {"query": firm["period"]})
        raise MockGaveUp("filing not listed")
    obs = yield ("click", {"ref": filing})
    m = re.search(r"SEC Accession No\.\s*(\d{10}-\d{2}-\d{6})", obs)
    if not m:
        raise MockGaveUp("no accession on index page")
    accession = m.group(1)
    folder = url_of(obs).rsplit("/", 1)[0] + "/"
    obs = yield ("goto", {"url": folder})
    fs = ref_on_line(obs, "FilingSummary.xml")
    if not fs:
        raise MockGaveUp("no FilingSummary.xml in folder")
    obs = yield ("click", {"ref": fs})
    obs = yield ("find_text", {"query": "<ShortName>"})
    # each hit line: "<Role>...</Role> / <ShortName>X</ShortName> / <MenuCategory>..." -- the R file is in
    # the matching <HtmlFileName> line; ask for it with a second search on the report title
    title = None
    for ln in obs.split("\n"):
        t = re.search(r"<ShortName>([^<]*balance sheets?[^<]*)</ShortName>", ln, re.I)
        if t and "parenthetical" not in t.group(1).lower():
            title = t.group(1)
            break
    if not title:
        raise MockGaveUp("no balance sheet report")
    obs = yield ("find_text", {"query": f"Statement - {title}"})
    h = re.search(r"<HtmlFileName>(R\d+\.htm)</HtmlFileName>\s*/\s*<LongName>[^<]*Statement - " + re.escape(title)
                  + r"</LongName>", obs)
    if not h:
        raise MockGaveUp("no HtmlFileName for " + title)
    obs = yield ("goto", {"url": folder + h.group(1)})
    scale, dates, rows = parse_r_page(obs)
    vals = find_row(rows, read["row"])
    if vals is None:
        obs = yield ("find_text", {"query": read["row"].split("'")[0]})
        raise MockGaveUp("row not found: " + read["row"])
    target = _date_text(firm["period"])
    col = dates.index(target) if target in dates else 0
    if read.get("column") == "other":
        col = 1 if col == 0 else 0
    v = vals[col]
    if read.get("minus_row"):
        sub = find_row(rows, read["minus_row"])
        v = v - sub[col]
    if read.get("scale", True):
        v = v * scale
    period_end = _iso(dates[col]) if col < len(dates) else None
    return dict(value_usd=int(round(v)), accession=accession, period_end=period_end, evidence_url=url_of(obs))


def _date_text(period):
    """'June 27, 2026' -> 'Jun. 27, 2026' (R-page column style; 'May' has no dot)."""
    mon, rest = period.split(" ", 1)
    short = mon[:3] + ("" if mon == "May" else ".")
    day, year = rest.replace(",", "").split()
    return f"{short} {int(day):02d}, {year}"


_MON = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
                                    "Nov", "Dec"], 1)}


def _iso(d):
    m = re.match(r"([A-Z][a-z]{2})\.? (\d{1,2}), (\d{4})", d)
    return f"{m.group(3)}-{_MON[m.group(1)]:02d}-{int(m.group(2)):02d}" if m else None


def persona_script(persona, task, key):
    """The whole run as a generator of tool calls. Ends by yielding submit_answer."""
    tid = task["id"]
    if task["kind"] == "rank":
        yield from _rank_script(persona, task, key)
        return
    firm = FIRMS[TASK_FIRM[tid]]
    read = dict(row=firm["row"], column="target", scale=True, minus_row=firm.get("minus_row"))
    try:
        if persona == "hallucinate":
            yield ("goto", {"url": SEARCH_URL})
            made_up = (int(key["value_usd"] * 1.0373) // 1_000_000) * 1_000_000 + 7_000_000
            yield ("submit_answer", {"value_usd": made_up, "accession": f"{firm['cik']:010d}-26-000099",
                                     "period_end": task["target_end"]})
            return
        if persona == "give_up":
            yield ("goto", {"url": SEARCH_URL})
            yield ("submit_answer", {"give_up": True})
            return
        if persona == "loop":
            obs = yield ("goto", {"url": SEARCH_URL})
            i = 0
            while True:                       # no new network traffic: re-reads the same page
                i += 1
                obs = yield (("read_page", {"page": 1}) if i % 2 else ("find_text", {"query": "Company Search"}))
        if persona == "api":
            yield ("goto", {"url": f"https://data.sec.gov/api/xbrl/companyconcept/CIK{firm['cik']:010d}"
                                   "/us-gaap/StockholdersEquity.json"})
        if persona == "comparative":
            read["column"] = "other"
        if persona == "units":
            read["scale"] = False
        if persona == "wrong_line":
            read["row"] = "Total liabilities and"
            read["minus_row"] = None
        if persona == "wrong_entity":
            firm = FIRMS[DECOY[tid]]
            read = dict(row=firm["row"], column="target", scale=True, minus_row=firm.get("minus_row"))
        res = yield from firm_path(firm, read)
        yield ("submit_answer", res)
    except MockGaveUp as e:
        yield ("submit_answer", {"give_up": True, "evidence_url": f"mock: {e}"})


def _rank_script(persona, task, key):
    bes, accs = {}, {}
    try:
        for fm in task["firms"]:
            firm = FIRMS[fm["ticker"]]
            read = dict(row=firm["row"], column="other" if persona == "comparative" else "target",
                        scale=persona != "units")
            res = yield from firm_path(firm, read)
            bes[fm["ticker"]] = res["value_usd"]
            accs[fm["ticker"]] = res["accession"]
    except MockGaveUp as e:
        yield ("submit_answer", {"give_up": True, "evidence_url": f"mock: {e}"})
        return
    me = task["market_equity"]["usd"]
    ranking = sorted(bes, key=lambda t: -bes[t] / me[t])
    yield ("submit_answer", {"book_equity_usd": bes, "ranking_high_to_low_bm": ranking})


# ---------------------------------------------------------------------------
# The model-like wrapper used by run_web.py
# ---------------------------------------------------------------------------
class MockModel:
    """Looks like the API to run_web.py: respond(messages) -> dict(content, stop_reason, usage)."""

    def __init__(self, persona, task, key):
        assert persona in PERSONAS, persona
        self.persona = persona
        self.gen = persona_script(persona, task, key)
        self.started = False
        self.n = 0

    def respond(self, messages):
        last = messages[-1]["content"]
        obs = ""
        if isinstance(last, list):
            obs = "\n".join(b.get("content", "") for b in last if isinstance(b, dict))
        try:
            if not self.started:
                self.started = True
                tool, args = next(self.gen)
            else:
                tool, args = self.gen.send(obs)
        except StopIteration:
            return dict(content=[{"type": "text", "text": "(mock finished)"}], stop_reason="end_turn",
                        usage=_usage(messages, 20))
        self.n += 1
        block = {"type": "tool_use", "id": f"toolu_mock_{self.n:03d}", "name": tool, "input": args}
        return dict(content=[block], stop_reason="tool_use", usage=_usage(messages, 60))


def _usage(messages, out_tokens):
    """Fake but plausible token counts: chars/4, with the earlier context counted as cache reads."""
    def size(m):
        c = m["content"]
        if isinstance(c, str):
            return len(c)
        return sum(len(str(b.get("content", b.get("input", b.get("text", ""))))) for b in c)
    total = sum(size(m) for m in messages) // 4 + 3000
    new = size(messages[-1]) // 4
    return dict(input_tokens=3, cache_creation_input_tokens=new, cache_read_input_tokens=max(0, total - new),
                output_tokens=out_tokens)
