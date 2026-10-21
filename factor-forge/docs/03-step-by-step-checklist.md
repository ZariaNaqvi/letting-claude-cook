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

## Week 3 — Oct 28 to Nov 3: analyze

### Step 12. Numbers and figures (Oct 28–30)
- [ ] Run `python analyze.py`. It writes:
  - `results/summary.md`
  - `results/pass_rates.csv`, `results/fisher_tests.csv`, `results/cost.csv`, `results/error_tags.csv`
  - `figures/pass_rate.png`, `figures/task_heatmap.png`, `figures/error_tags.png`
- [ ] Read the summary and figures:
  ```bash
  code results/summary.md
  open figures/*.png
  ```
  For each hypothesis H1–H3, write one sentence in `notes.txt`: supported, not supported, or unclear, and why. See [code/07-analyze.md](code/07-analyze.md).
- [ ] Commit, tag `results-v1`, and push.

### Step 13. The stories behind the numbers (Oct 31–Nov 2)
- [ ] Pick 3 interesting failures and 1 impressive success. Read each model's own explanation in `response.txt`.
- [ ] Look for "right number, wrong reasons" or "wrong number, right reasoning." These make the best talk slides.

---

## Week 4 — Nov 3 to Nov 11: write, present, publish

- [ ] **Write-up (Nov 3–8):** 4–6 pages. Sections: question, data, method, results, error analysis, limitations, conclusion. See the guide, Part 3, section 4.
- [ ] **Talk (Nov 6–10):** about 9 slides in 10 minutes, built around the pass-rate figure. Rehearse out loud twice with a timer.
- [ ] **Portfolio (Nov 9–11):**
  - Polish `README.md` with the headline figure.
  - Check for leaked keys before making the repo public: `git log -p | grep "sk-ant-" | grep -v "sk-ant-REPLACE-ME"` must print nothing.
  - Add the resume bullet with your real numbers.

## If you fall behind: the smaller version

Run 3 models (opus, sonnet, haiku) on 4 factors (HML, SMB_5F, MOM, ST_REV), 3 repeats each:
```bash
python run_experiment.py --models opus sonnet haiku --tasks HML SMB_5F MOM ST_REV --repeats 3
python score.py
python analyze.py
```
That is 72 runs, which is still a real, defensible result.

Next: [04 — The data and its traps](04-the-data-and-its-traps.md)
