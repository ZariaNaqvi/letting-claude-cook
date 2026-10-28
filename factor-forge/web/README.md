# Form Forge (Part 3): book equity through the SEC EDGAR web forms

Part 2 handed the models tidy CSV previews, and they tied (316/320 PASS). Part 3 takes away the
files and the Python. Each model gets only a headless browser, driven through tools. It has to
click through SEC EDGAR to find a company's **book equity** in a 10-Q or 10-K filed after
July 1, 2026, which is past every model's training cutoff. The path runs from the company search
form, to the filings list, to the filing index, to FilingSummary.xml, to the balance-sheet R page.
The design is in `../docs/06-part3-form-forge-design.md`.

The answer key comes from SEC's XBRL API, `data.sec.gov/api/xbrl`. The models' browser **cannot
reach that API**. Grading is exact (tolerance $0) and automatic, and it uses error tags, the same
way Part 2 did.

## Files

| file | purpose |
|---|---|
| `tasks_web.json` | the 8 tasks (T1-T7 one firm each, T8 a 4-firm B/M ranking), with goal text, STEPS click path, units hint, answer schema, step cap, and frozen answers |
| `answer_key.py` | fetches companyfacts + frames (11 requests), then freezes `answer_key.json` and `data/raw/*.json.gz` (with sha256). `--check` re-verifies everything with no network |
| `prompts_web.py` | the system prompt plus the STEPS / GOAL_ONLY prompt builder. The wording is the same for every model (`PROMPT_VERSION`) |
| `sec_policy.py` | the access policy: allowed hosts, SEC robots.txt rules, the blocked XBRL API, at most 5 requests/s, the declared User-Agent, the asset cache, and fixture record/replay |
| `browser_tools.py` | the Playwright wrapper. It renders text with inline `[eN kind]` refs, splits pages into 10,000-character chunks, and runs the 9 tools (goto, read_page, find_text, click, fill, select_option, press, back, submit_answer) |
| `run_web.py` | the agent loop. It uses Messages API tool use, prompt caching, a step cap and time limit, per-step logs, cost accounting, a budget guard, and resume. `--dry-run`, `--offline` and `--pilot` select the run type |
| `mock_agent.py` | the fake model for `--dry-run`. Its 9 scripted personas drive the real browser and plant known mistakes |
| `capture_fixtures.py` | records the live pages once for offline tests (`fixtures/`) |
| `score_web.py` | assigns PASS plus an error tag and writes `runs_scored.csv`. In a dry run it also checks each persona's planted mistake |
| `selftest_web.py` | runs the policy, rate-limit, User-Agent and scorer checks (planted mistakes on all 8 tasks), plus an offline end-to-end run of every persona. No API, no network |
| `analyze_web.py` | computes Wilson CIs and Fisher tests (H1-H5), cost per correct answer and steps per success, and draws 3 figures and `summary.md` |

## Exact commands

```bash
cd ~/letting-claude-cook/factor-forge && source .venv/bin/activate
pip install -r web/requirements-web.txt
python -m playwright install chromium
# add to .env (your name + a contact address you choose; never commit .env):
#   SEC_USER_AGENT="Firstname Lastname contact@yourdomain"

python web/answer_key.py --check          # the key is already frozen; re-verify offline (no network)
python web/selftest_web.py                # must end "ALL CHECKS PASSED" (no API, no network)
python web/run_web.py --dry-run --tasks T1 T4 --conds STEPS --repeats 1 --out runs_web_mock   # live site, fake model, $0
python web/score_web.py --runs runs_web_mock --out results_web_mock      # "0 mismatches"
python web/analyze_web.py --in results_web_mock/runs_scored.csv --out results_web_mock

# pilot (real API, about $5-7): read every transcript afterwards
python web/run_web.py --pilot --models haiku sonnet --tasks all --conds STEPS GOAL_ONLY --repeats 1 --out runs_web_pilot
python web/run_web.py --pilot --models fable opus --tasks T1 T4 --conds GOAL_ONLY --repeats 1 --out runs_web_pilot
python web/score_web.py --runs runs_web_pilot --out results_web_pilot

# main run (192 runs, resume-safe, stops itself before passing $100)
python web/run_web.py --models fable opus sonnet haiku --tasks all --conds STEPS GOAL_ONLY \
       --repeats 3 --effort high --budget-usd 100 --out runs_web 2>&1 | tee -a runlog_web.txt
python web/score_web.py --runs runs_web --out results_web
python web/analyze_web.py --in results_web/runs_scored.csv --part2 results/runs_scored.csv --out results_web
```

The list flags take spaces or commas: `--tasks T1,T4` is the same as `--tasks T1 T4`.

The same steps with dates, expected outputs and checkpoints are Steps 12-18 of `../docs/03-step-by-step-checklist.md`. Before the pilot, run `python web/capture_fixtures.py --all` (only T1 and T4 were walked live) and set `PROMPT_VERSION = "web-v1"` in `prompts_web.py`.

## How the browser reaches SEC

Every request the page makes goes through `sec_policy.Policy.handle`. Allowed requests are then
made by a plain HTTP client (`httpx2`), not by Chromium itself. That client sends **only the
declared User-Agent**, follows redirects itself, and waits for the rate limiter on every hop.
Chromium just renders the answer. We tested a direct headless-Chromium fetch first, and SEC answered
`403 Undeclared Automated Tool` even with a declared User-Agent. With the plain client, every
request is the kind SEC's fair-access page asks automated tools to send. Nothing is disguised:
there is no browser User-Agent and there are no fingerprint headers.

If SEC still answers 403, the harness stops the run as a `HARNESS_ERROR` and stops the whole
session. Wait at least 10 minutes and check `SEC_USER_AGENT`. If it keeps happening, use the NY Fed
fallback in design §1 and log it in `notes.txt`.
