# 3. Step-by-step checklist

This is the short version of the full guide, with every command and why it is there. Tick boxes as you go. For full detail on any step, open the [Factor Forge guide](https://claude.ai/artifact/HToxdCErddTAecizX4zbfk).

**Where you type things:**
- **Terminal:** macOS Terminal, or the terminal built into VS Code (<kbd>Ctrl</kbd>+<kbd>`</kbd>).
- **VS Code:** for reading and editing files.
- **Browser:** for GitHub and the Anthropic Console.

**Two habits for every session:**
```bash
cd ~/letting-claude-cook/factor-forge
source .venv/bin/activate        # your prompt should now start with (.venv)
```
*Why:* `cd` puts you in the project folder. `source .venv/bin/activate` switches to this project's own Python and libraries, so nothing changes under you mid-experiment.

**Where the tested code lives:** `~/factor-forge-build/` holds a tested copy of every file. You copy files from there into the project as each step needs them. Read each one (or its explainer in `docs/code/`) before you use it.

---

## Week 1 — Oct 14 to Oct 20: set up and build the answer key

### Step 1. Accounts (Oct 14)
- [ ] **GitHub:** check that your fork is connected.
  ```bash
  cd ~/letting-claude-cook
  git remote -v           # should list origin (ZariaNaqvi/...) and upstream (dfink/...)
  git fetch upstream && git merge upstream/main
  ```
  *Why:* your work goes to your fork, and you pull new course material from upstream.
- [ ] **Anthropic API key:**
  - First, ask course staff whether the class has API credits.
  - Otherwise, go to **console.anthropic.com**, sign up, add about $50–100 in credits, set a **monthly spend limit**, and create an API key (it starts with `sk-ant-`).
  - *Why:* the experiment calls the models from Python through the API, not through the claude.ai chat window. That way every model gets exactly the same input and every response is logged.
- [ ] **Python 3.10 or newer:** `python3 --version`. If it is older, run `brew install python@3.12`.

### Step 2. Project folder and environment (Oct 14)
- [ ] Make the virtual environment:
  ```bash
  cd ~/letting-claude-cook/factor-forge
  python3 -m venv .venv
  source .venv/bin/activate
  ```
  *Why:* a venv is a private copy of Python for this project. The model-written scripts run on these exact library versions, which keeps the runs comparable.
- [ ] Copy the config files and install the libraries:
  ```bash
  cp ~/factor-forge-build/{requirements.txt,.gitignore,.env.example} .
  pip install --upgrade pip
  pip install -r requirements.txt
  ```
- [ ] Store your key safely:
  ```bash
  cp .env.example .env
  chmod 600 .env          # only you can read it
  code .env               # replace sk-ant-REPLACE-ME with your real key, save
  git check-ignore -v .env   # must print a line, which means git will never commit it
  ```
- [ ] Start your lab notebook: create `notes.txt` and write today's date and what you set up.
- [ ] First commit:
  ```bash
  cd ~/letting-claude-cook
  git add factor-forge/.gitignore factor-forge/.env.example factor-forge/requirements.txt factor-forge/notes.txt factor-forge/docs
  git commit -m "factor-forge: project skeleton and docs"
  git push origin main
  ```

### Step 3. Download Ken French's raw files (Oct 15)
- [ ] Download and unzip the 11 files:
  ```bash
  cd ~/letting-claude-cook/factor-forge
  mkdir -p data/zips data/raw
  for n in F-F_Research_Data_Factors F-F_Research_Data_5_Factors_2x3 \
           F-F_Momentum_Factor F-F_ST_Reversal_Factor F-F_LT_Reversal_Factor \
           6_Portfolios_2x3 6_Portfolios_ME_OP_2x3 6_Portfolios_ME_INV_2x3 \
           6_Portfolios_ME_Prior_12_2 6_Portfolios_ME_Prior_1_0 6_Portfolios_ME_Prior_60_13; do
    curl -fSL -o "data/zips/${n}_CSV.zip" \
      "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/${n}_CSV.zip" &&
    unzip -o -q "data/zips/${n}_CSV.zip" -d data/raw
  done
  ls data/raw
  ```
  *Why:* these are the exact inputs the models get. Five files hold the official answers (the factor files), and six hold the 2×3 portfolios the factors are built from.
- [ ] Open `data/raw/6_Portfolios_2x3.csv` in VS Code and scroll through it. Find where the value-weighted monthly table ends and the equal-weighted one starts. Seeing the traps yourself helps when you explain them in the talk. See [04 — The data and its traps](04-the-data-and-its-traps.md).

### Step 4. Build the answer key (Oct 16–18)
- [ ] `cp ~/factor-forge-build/ground_truth.py .` and read [code/01-ground_truth.md](code/01-ground_truth.md).
- [ ] List the tables inside each file: `python -I ground_truth.py --blocks | head -12`
- [ ] Build the answer key: `python -I ground_truth.py`
  *What it does:* parses the right tables, applies each factor's official formula, compares the result with French's official series, and writes `data/truth/` (official answers) and `data/reference/` (your rebuild).
  *Done when:* all 8 rows show correlation 1.0000 and RMSE under 1 bp (about 0.28–0.42).
  *Why:* this proves the task can be solved and sets the pass threshold. If you can't hit under 1 bp, you can't expect a model to.

### Step 5. Freeze the task list (Oct 18)
- [ ] `cp ~/factor-forge-build/make_tasks.py .` then `python -I make_tasks.py .`
  *What it does:* writes `tasks.json`, with one entry per factor: input files, the recipe text, which table, and the official file and column. See [code/02](code/02-make_tasks-and-tasks-json.md).
  Line 35 of `make_tasks.py` says `downloaded 2026-10-14`. Change it to the day you downloaded the files, then re-run.

### Step 6. Commit and tag (Oct 19–20)
- [ ] Commit and tag the answer key:
  ```bash
  cd ~/letting-claude-cook
  git add factor-forge/ground_truth.py factor-forge/make_tasks.py factor-forge/tasks.json \
          factor-forge/data/raw factor-forge/data/truth factor-forge/data/reference \
          factor-forge/data/ground_truth_results.csv factor-forge/notes.txt
  git commit -m "factor-forge: raw French data, ground truth for 8 factors, tasks.json"
  git tag ground-truth-v1
  git push origin main --tags
  ```
  *Why:* a tag is a permanent bookmark, so you can always point to the exact data your results came from.

---

## Week 2 — Oct 21 to Oct 27: run the experiment

### Step 7. Bring in the harness (Oct 21)
- [ ] Copy the harness files and reinstall:
  ```bash
  cd ~/letting-claude-cook/factor-forge
  cp -n ~/factor-forge-build/{prompts.py,run_experiment.py,score.py,analyze.py,dryrun_mock.py,selftest.py,README.md} .
  pip install -r requirements.txt
  ```
- [ ] Look at the real prompts the models will see:
  ```bash
  python prompts.py HML RECIPE
  python prompts.py HML NAME_ONLY
  ```
  Read both all the way through. This is your experiment's "treatment." See [code/03-prompts.md](code/03-prompts.md).
- [ ] Freeze the prompts:
  ```bash
  cd ~/letting-claude-cook
  git add factor-forge/prompts.py factor-forge/tasks.json
  git commit -m "Factor Forge: prompt builder v1"
  git tag prompts-v1
  git push origin main --tags
  ```

### Step 8. Test everything for free (Oct 22)
- [ ] Run the self-test: `python selftest.py`. Done when it says all checks passed.
- [ ] Run a dry run with a fake model, then score it:
  ```bash
  python run_experiment.py --dry-run --repeats 2
  python score.py --dry-run
  ```
  *Why:* the fake model returns correct scripts most of the time and deliberately broken ones (sign flip, wrong table, ×100, crash) the rest of the time. If the scorer tags every planted mistake correctly, you can trust it on real runs. It costs $0. See [code/05](code/05-dryrun_mock-and-selftest.md).

### Step 9. Pilot: 8 real calls (Oct 23)
- [ ] Make one call to the cheapest model first:
  ```bash
  python run_experiment.py --models haiku --tasks HML --conditions RECIPE --repeats 1 --out runs_pilot
  ```
- [ ] Run the pilot: HML × both conditions × 4 models.
  ```bash
  python run_experiment.py --tasks HML --repeats 1 --out runs_pilot
  ```
- [ ] **Read every pilot run by hand.** Each folder `runs_pilot/<model>/HML/<condition>/r1/` has `response.txt` (what the model said), `solution.py` (the code it wrote), `stderr.txt` (any errors), `output.csv` and `meta.json` (tokens, cost, time).
- [ ] Score the pilot and check the spend:
  ```bash
  python score.py --runs runs_pilot --out results_pilot
  ```
  Also check your spend in the Anthropic Console. Multiply the pilot cost by 40 to estimate the full run.

### Step 10. Full run: 320 calls (Oct 24–25)
- [ ] Commit the harness first: `git add` the `.py` files plus `README.md` and `notes.txt`, then commit and push. See the guide, section 5.
- [ ] Start the full run:
  ```bash
  cd ~/letting-claude-cook/factor-forge
  caffeinate -i python run_experiment.py --repeats 5 2>&1 | tee -a runlog.txt
  ```
  - `caffeinate -i` stops your Mac from sleeping during the run.
  - `tee -a runlog.txt` shows the output on screen and saves it to a log.
- [ ] If it stops partway through, run the **same command again**. It skips finished runs.
- [ ] If you see `429 rate limit` errors, add `--workers 1`.

### Step 11. Score and hand-check (Oct 26–27)
- [ ] Score every run: `python score.py` writes `results/runs_scored.csv`, with 320 rows.
- [ ] Open 10 random runs and check that you agree with the tag the scorer gave each one. Write what you find in `notes.txt`.
- [ ] Make sure no key leaked: `grep -rl "sk-ant-" runs runs_pilot` must print nothing.
- [ ] Commit `runs/`, `results/`, `notes.txt` and `runlog.txt`, then tag `run-v1` and push.

---

## Week 3 — Oct 28 to Nov 3: Part 3, Form Forge (the harder test)

Part 2 ended at 316/320 PASS, so the models tied. In Part 3 each model gets only a web browser and must click through SEC EDGAR to find book equity in filings made after July 1, 2026. Read [06 — Part 3 design](06-part3-form-forge-design.md) first. The code is already in `web/` and was tested on Oct 28 with a fake model only (no API calls).

Every command below runs from `~/letting-claude-cook/factor-forge` with the venv active.

### Step 12. Set up the browser and your SEC User-Agent (Oct 28)
- [ ] Install Playwright and its browser:
  ```bash
  pip install -r web/requirements-web.txt
  python -m playwright install chromium
  pip show playwright | head -2        # Version: 1.64.1
  ```
  *Why:* the models drive a real headless Chrome. `requirements-web.txt` first installs Part 2's pins (`-r ../requirements.txt`), so pandas, numpy and anthropic don't change.
- [ ] Add your SEC User-Agent to `.env` (open it with `code .env`; never commit it):
  ```
  SEC_USER_AGENT="Firstname Lastname contact@yourdomain"
  ```
  *Why:* SEC asks every automated tool to say who runs it. The harness refuses to start if this line is missing, still the placeholder from `.env.example`, or the test value.
- [ ] Check it loads (prints only a hash, never the address):
  ```bash
  python -c "import sys; sys.path.insert(0,'web'); import sec_policy; print(sec_policy.ua_digest(sec_policy.load_user_agent())[:12])"
  ```
  *Done when:* it prints 12 hex characters. An error starting `SEC_USER_AGENT is missing` means the `.env` line is wrong.
- [ ] Write the Playwright version and today's setup in `notes.txt`.

### Step 13. Check the frozen answer key (Oct 28–29)
- [ ] Re-verify the key with no network:
  ```bash
  python web/answer_key.py --check
  ```
  *Expected output (shortened):*
  ```
  sha256 OK for 11 raw files
  T1    Apple Inc.                      107,520,000,000 0000320193-26-000020   10-Q  2026-07-31 2026-06-27
  T2    Microsoft Corporation           442,387,000,000 0001193125-26-323660   10-K  2026-07-29 2026-06-30
  T3    Walmart Inc.                     98,238,000,000 0000104169-26-000154   10-Q  2026-08-28 2026-07-31
  T4    Netflix, Inc.                    30,152,052,000 0001065280-26-000212   10-Q  2026-07-17 2026-06-30
  T5    Domino’s Pizza, Inc.             -3,982,431,000 0001286681-26-000035   10-Q  2026-07-20 2026-06-14
  T6    JPMORGAN CHASE & CO             353,558,000,000 0001628280-26-054343   10-Q  2026-08-06 2026-06-30  (SE 374,598,000,000 - preferred 21,040,000,000)
  T7    BERKSHIRE HATHAWAY INC          747,910,000,000 0001193125-26-341032   10-Q  2026-08-10 2026-06-30
  T8    ranking high->low B/M: ['CVX', 'KO', 'MMM', 'AAPL']
  frozen key matches a rebuild from raw files: True
  ```
  *Checkpoints:* T1 is `107,520,000,000 0000320193-26-000020`; T2's form is `10-K`; T6's preferred is non-zero (21,040,000,000).
  *Why:* the key was fetched on Oct 28 from SEC's XBRL API (11 requests) and saved with sha256 hashes. `--check` proves nothing changed.
- [ ] Optional: refetch with your own User-Agent (the key was frozen with the test one; the data is the same):
  ```bash
  python web/answer_key.py --force       # 11 SEC requests, overwrites web/answer_key.json and the answers in tasks_web.json
  python web/answer_key.py --check
  ```
- [ ] Record the T8 market-equity source in `notes.txt`: shares outstanding on each 10-Q cover × the June 30, 2026 close (AAPL 289.36, KO 81.27, CVX 165.76, MMM 161.91, Yahoo Finance daily history, read 2026-10-28).

### Step 14. Walk every STEPS path by hand, then capture the pages (Oct 29)
- [ ] Print each task's prompt and follow its STEPS in Chrome, starting at https://www.sec.gov/search-filings:
  ```bash
  python web/prompts_web.py T2 STEPS      # then T3, T5, T6, T7, T8 (T1 and T4 were already walked live)
  ```
  Check every button label, report title, row name and column date against the live page.
- [ ] If a label differs, fix it in `web/tasks_web.json` (the `steps` text) **and** in the `FIRMS` table at the top of `web/mock_agent.py` (`search`, `suggestion`, `period`, `row`).
- [ ] Save the pages for offline tests (about 40–60 requests per task, at most 5 per second):
  ```bash
  python web/capture_fixtures.py --all
  ```
  *Expected:* for every task, `-> matches the key; N network requests; max 5 requests in any 1 s window`, then `fixtures: N saved responses`. On Oct 28, T1 used 41 requests and T4 39.
  *If a task says `DOES NOT match the key`:* its STEPS wording or mock labels are off. Fix them and rerun that task: `python web/capture_fixtures.py --tasks T6`.
  *If it prints `SEC answered 403`:* stop, wait at least 10 minutes, and check `SEC_USER_AGENT`.
- [ ] Freeze the prompts: in `web/prompts_web.py` change `PROMPT_VERSION = "web-v1-draft"` to `PROMPT_VERSION = "web-v1"`, and `"version"` at the top of `web/tasks_web.json` to `"web-v1"`. Then commit and tag:
  ```bash
  cd ~/letting-claude-cook
  git add factor-forge/web factor-forge/docs factor-forge/.env.example factor-forge/.gitignore factor-forge/README.md factor-forge/notes.txt
  git status                              # .env and web/.asset_cache must NOT be listed
  git commit -m "Form Forge: Part 3 harness, frozen answer key, prompts web-v1"
  git tag prompts-web-v1
  git push origin main --tags
  ```

### Step 15. Test everything for free (Oct 29)
- [ ] Self-test (no API, no network, 1–3 minutes):
  ```bash
  python web/selftest_web.py
  ```
  *Done when:* it ends with `148/148 checks passed` and `ALL CHECKS PASSED`. It checks the access rules (A), the rate limit (B), the User-Agent refusal (C), every planted mistake on all 8 tasks (D), the API request shape against a fake server (F), and all 9 personas end to end offline on T1 and T4 (E).
- [ ] Fake model on the saved pages, all 8 tasks (no network):
  ```bash
  python web/run_web.py --dry-run --offline --tasks all --conds STEPS --repeats 1 --out runs_web_mock/offline
  python web/score_web.py --runs runs_web_mock/offline --out results_web_mock/offline
  ```
  *Done when:* the last lines say `0 mismatches`. Every persona gets its planted tag (good and api → PASS, comparative → WRONG_PERIOD, units → UNITS, wrong_line → WRONG_LINE, wrong_entity → WRONG_ENTITY, hallucinate → UNGROUNDED, give_up → GAVE_UP, loop → STEP_LIMIT).
- [ ] Look at one run folder, e.g. `runs_web_mock/offline/T1__STEPS__mock-good__r1/`: `prompt.txt`, `steps.jsonl`, `pages/step_01.txt` … (exactly what the model saw), `requests.jsonl`, `transcript.json`, `final.json`.
- [ ] Run the analysis on the fake runs, to check the figures work:
  ```bash
  python web/analyze_web.py --in results_web_mock/offline/runs_scored.csv --part2 results/runs_scored.csv --out results_web_mock/offline
  ```
  It ends with `wrote ... summary.md, 5 CSVs and 3 figures`. The summary is headed **DRY RUN … NOT real results**.

  (The live-site dry run from Oct 28 is already in `runs_web_mock/`: 18 runs on T1 and T4, `0 mismatches`. Rerunning `python web/run_web.py --dry-run --tasks T1 T4 --conds STEPS --repeats 1 --out runs_web_mock` prints `18 runs requested, 18 already done, 0 to do`.)

### Step 16. Pilot: about 36 real runs (Oct 30), about $5–7
- [ ] **Before any paid call:** read the "How the browser reaches SEC" note in `web/README.md` and decide you are comfortable with it (a plain HTTP client sends your declared User-Agent; Chromium only renders).
- [ ] Check `ANTHROPIC_API_KEY` and `SEC_USER_AGENT` are both in `.env`. Check your Console spend limit.
- [ ] Run the pilot (one run at a time; each takes about 2–5 minutes):
  ```bash
  python web/run_web.py --pilot --models haiku sonnet --tasks all --conds STEPS GOAL_ONLY --repeats 1 --out runs_web_pilot
  python web/run_web.py --pilot --models fable opus --tasks T1 T4 --conds GOAL_ONLY --repeats 1 --out runs_web_pilot
  python web/score_web.py --runs runs_web_pilot --out results_web_pilot
  ```
  Each finished run prints one line like `[3/32] T1|STEPS|sonnet|r1 stop=answered steps=12 value=... accn=... blocked=0 net=... tok=.../... $0.2 ...s`.
- [ ] **Read every pilot transcript** (`runs_web_pilot/*/transcript.json` and `pages/`). Look for harness problems: pages that came back empty, refs that didn't work, SEC errors.
- [ ] Measure the cost per run:
  ```bash
  python -c "import pandas as pd; d=pd.read_csv('results_web_pilot/runs_scored.csv'); print(d.groupby('model_alias').cost_usd.agg(['count','mean','sum']))"
  ```
  **Repeat rule:** projected cost = sum over models of (mean cost per run × 48). If it is over $100, use `--repeats 2` in Step 17 (128 runs). Write the numbers and the decision in `notes.txt` **before** the main run.
- [ ] Pilot runs are never pooled with the main run.

### Step 17. Main run: 192 runs (Oct 31 – Nov 1), at most $100
- [ ] Start it (about 8–14 hours in total, so spread it over 2–3 sessions):
  ```bash
  caffeinate -i python web/run_web.py --models fable opus sonnet haiku --tasks all --conds STEPS GOAL_ONLY \
         --repeats 3 --effort high --budget-usd 100 --out runs_web 2>&1 | tee -a runlog_web.txt
  ```
  - Order is repeat-major: every task × condition × model for r1, then r2, then r3. If it stops early, every model has the same number of finished repeats.
  - **Ctrl-C is safe.** Rerun the same command; runs with a `final.json` are skipped (harness errors are redone).
  - `BUDGET STOP: spent $..., next run could cost up to $...` means the $100 cap was reached. Stop there and write it in `notes.txt`.
  - `SEC returned HTTP 403 ... Stopping ALL runs` means SEC blocked the harness. Wait at least 10 minutes, check `SEC_USER_AGENT`, rerun. If it keeps happening, use the NY Fed fallback (design §1) and log it as a protocol deviation.
- [ ] Watch spend in the Anthropic Console.

### Step 18. Score, hand-check, analyze (Nov 2–3)
- [ ] Score and analyze:
  ```bash
  python web/score_web.py --runs runs_web --out results_web
  python web/analyze_web.py --in results_web/runs_scored.csv --part2 results/runs_scored.csv --out results_web
  ```
  This writes `results_web/runs_scored.csv`, `pass_rates.csv`, `fisher_tests.csv`, `error_tags.csv`, `efficiency.csv`, `behavior.csv`, `summary.md` and `fig_task_heatmap.png`, `fig_cost_per_correct.png`, `fig_steps_success.png`.
- [ ] **Hand-check 20 runs:** all `OTHER_WRONG` runs plus a random sample of passes and failures. Read `pages/` and `transcript.json` and say whether you agree with each tag. If the scorer is wrong, fix `score_web.py` and **rescore; never rerun**.
- [ ] Leak checks, both must print nothing:
  ```bash
  grep -rl "sk-ant-" runs_web runs_web_pilot
  grep -rl "your-contact-address" runs_web runs_web_pilot     # put your real SEC contact address here
  ```
- [ ] Write the headline numbers and H1–H5 verdicts in `notes.txt`. Commit `web/`, `runs_web_pilot/`, `results_web_pilot/`, `runs_web/`, `results_web/`, `runlog_web.txt` and `notes.txt`; tag `run-web-v1`; push.

---

## Week 4 — Nov 4 to Nov 11: Part 4, analyze, write, present

### Step 19. Combined analysis (Nov 4)
- [ ] Run the Part 2 analysis (free, no API): `python analyze.py`. It writes:
  - `results/summary.md`
  - `results/pass_rates.csv`, `results/fisher_tests.csv`, `results/cost.csv`, `results/error_tags.csv`
  - `figures/pass_rate.png`, `figures/task_heatmap.png`, `figures/error_tags.png`
- [ ] Read both summaries and all figures:
  ```bash
  code results/summary.md results_web/summary.md
  open figures/*.png results_web/*.png
  ```
  For each hypothesis (Part 2 H1–H3, Part 3 H1–H5), write one sentence in `notes.txt`: supported, not supported, or unclear, and why. See [code/07-analyze.md](code/07-analyze.md) and [code/15](code/15-score_web-and-analyze_web.md).
- [ ] Commit, tag `results-v1`, and push.

### Step 20. The stories behind the numbers (Nov 5)
- [ ] Pick 6–8 runs to annotate: Part 2 failures (read `response.txt`) and Part 3 transcripts. Look for "right number, wrong row", "right page, wrong column", "never found the filing", and guesses.
- [ ] These make the best talk slides.

### Step 21. Write, present, publish (Nov 6–11)
- [ ] **Write-up (Nov 6–8):** 4–6 pages. Sections: question, data, method, Part 2 results, Part 3 results (its own section), error analysis, limitations, conclusion. See the guide, Part 4.
- [ ] **Talk (Nov 9–10):** about 11 slides in 10 minutes, built around the pass-rate figure, plus 2 new slides: the EDGAR click path, and the Part 2 vs Part 3 table. Rehearse out loud twice with a timer.
- [ ] **Portfolio (Nov 10–11):**
  - Polish `README.md` with the headline figures and the Part 3 results.
  - Check for leaked keys before making the repo public: `git log -p | grep "sk-ant-" | grep -v "sk-ant-REPLACE-ME"` must print nothing. Do the same for your SEC contact address.
  - Add the resume bullet with your real numbers.
- [ ] **Nov 11: submit** the paper, repo and talk.

## If you fall behind: the smaller version

Run 3 models (opus, sonnet, haiku) on 4 factors (HML, SMB_5F, MOM, ST_REV), 3 repeats each:
```bash
python run_experiment.py --models opus sonnet haiku --tasks HML SMB_5F MOM ST_REV --repeats 3
python score.py
python analyze.py
```
That is 72 runs, which is still a real, defensible result.

**Smaller Part 3**, if the pilot is slow or costly: 2 repeats instead of 3 (128 runs), or fewer tasks and models:
```bash
python web/run_web.py --models opus sonnet haiku --tasks T1 T3 T4 T5 T6 --conds STEPS GOAL_ONLY --repeats 2 --budget-usd 60 --out runs_web
python web/score_web.py --runs runs_web --out results_web
python web/analyze_web.py --in results_web/runs_scored.csv --part2 results/runs_scored.csv --out results_web
```
That is 60 runs. Write the change in `notes.txt` before you start.

Next: [04 — The data and its traps](04-the-data-and-its-traps.md)
