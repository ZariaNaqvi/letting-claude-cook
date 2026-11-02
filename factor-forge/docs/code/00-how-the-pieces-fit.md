# 00 - How the pieces fit

Factor Forge tests whether Claude models can rebuild 8 official Fama-French factors (HML, SMB_3F, SMB_5F, RMW, CMA, MOM, ST_REV, LT_REV) from Ken French's raw portfolio CSV files. Each model writes a Python script. The harness runs the script and scores its output against the official series. PASS = the script runs, covers at least 95% of the official months, and has RMSE of at most 1 basis point.

8 tasks x 2 conditions (RECIPE, NAME_ONLY) x 4 models x 5 repeats = 320 runs.

## The flow

```mermaid
flowchart TD
    RAW["data/raw/*.csv<br/>Ken French raw files"] --> GT["ground_truth.py"]
    GT --> TRUTH["data/truth/TASK.csv<br/>official series"]
    GT --> REF["data/reference/TASK.csv<br/>human rebuild"]
    GT --> GTR["data/ground_truth_results.csv"]
    GTR --> MT["make_tasks.py"]
    MT --> TJ["tasks.json<br/>8 tasks + pass rule"]
    TJ --> PR["prompts.py"]
    RAW --> PR
    PR --> RE["run_experiment.py"]
    RE --> API["Claude API<br/>(or dryrun_mock.py with --dry-run)"]
    API --> SCRIPT["solution.py<br/>model's script"]
    SCRIPT --> RUN["run in temp folder<br/>raw inputs only, 60 s limit"]
    RUN --> OUT["runs/model/task/condition/rK/<br/>output.csv + meta.json"]
    OUT --> SC["score.py"]
    TRUTH --> SC
    TJ --> SC
    SC --> RS["results/runs_scored.csv"]
    RS --> AN["analyze.py"]
    AN --> FIG["figures/*.png"]
    AN --> SUM["results/summary.md<br/>+ CSV tables"]
```

In words:

1. **Answer key.** `ground_truth.py` reads the raw CSVs and the official factor files. It saves the official series to `data/truth/` and its own rebuild to `data/reference/`, and shows the rebuild matches to within rounding (0.28 to 0.42 bp).
2. **Task list.** `make_tasks.py` uses those results to write `tasks.json`: the 8 tasks, the prompt text for both conditions, and the pass rule (1.0 bp).
3. **Prompts.** `prompts.py` turns a task and a condition into the exact prompt text, including the first 60 lines of each raw input file.
4. **Runs.** `run_experiment.py` sends each prompt to a model, extracts the script from the reply, runs it in a clean temp folder that holds only the raw input files, and saves everything.
5. **Scoring.** `score.py` compares each `output.csv` with `data/truth/` and gives PASS or an error tag.
6. **Analysis.** `analyze.py` makes the pass-rate tables, statistical tests, cost table, figures and summary.

`dryrun_mock.py` and `selftest.py` sit beside this chain. They test it for free with fake scripts that contain known mistakes.

The raw CSVs come from the zips in `data/zips/` (downloaded from the Ken French Data Library; the URL pattern is in `tasks.json`). No script in the project downloads them.

## The files at a glance

All commands are run from inside `~/letting-claude-cook/factor-forge` with the venv active (`source .venv/bin/activate`).

| file | what it does in one line | when you run it | command | what it reads | what it writes |
|---|---|---|---|---|---|
| `ground_truth.py` | Rebuilds the 8 factors by hand and checks them against French's official series | Once, after downloading data (again only if data changes) | `python -I ground_truth.py` | `data/raw/*.csv` | `data/truth/*.csv`, `data/reference/*.csv`, `data/ground_truth_results.csv` |
| `make_tasks.py` | Writes the task definitions and pass threshold | Once, after `ground_truth.py` | `python make_tasks.py .` | `data/ground_truth_results.csv` | `tasks.json` |
| `tasks.json` | The 8 tasks, prompt texts, answer paths, pass rule, forbidden files | Not run; a data file | (none) | (read by other scripts) | (written by `make_tasks.py`) |
| `prompts.py` | Builds the exact prompt for one task and condition | Imported by the harness; run by hand to inspect a prompt | `python prompts.py HML RECIPE` | `tasks.json`, `data/raw/*.csv` | nothing (prints the prompt) |
| `run_experiment.py` | Calls the models, extracts and runs their scripts, saves every run | For the pilot and the full experiment | `python run_experiment.py --repeats 5` (free test: add `--dry-run`) | `tasks.json`, `data/raw/*.csv`, `.env` | `runs/` (or `runs_dryrun/`): per-run folders and `manifest.json` |
| `dryrun_mock.py` | Fake model that returns correct or deliberately broken scripts | Never directly; used by `--dry-run` and `selftest.py` | (none) | nothing | nothing (returns text) |
| `selftest.py` | Plants every known mistake on every task and checks the scorer tags it right | Before any real run, and after changing the harness or scorer | `python selftest.py` | `tasks.json`, `data/raw/`, `data/truth/` | nothing kept (uses a temp folder); prints `90/90 checks passed` |
| `score.py` | Grades every run: PASS or an error tag | After runs finish (rerun any time) | `python score.py` (or `--dry-run`) | `runs/*/.../meta.json` and `output.csv`, `tasks.json`, `data/truth/`, `data/raw/` | `results/runs_scored.csv` (dry run also `dryrun_check.csv`) |
| `analyze.py` | Pass rates with CIs, Fisher tests, cost, figures, summary | After `score.py` | `python analyze.py` (or `--dry-run`) | `results/runs_scored.csv`, `tasks.json` | `results/pass_rates.csv`, `fisher_tests.csv`, `task_pass_rates.csv`, `cost.csv`, `error_tags.csv`, `summary.md`; `figures/pass_rate.png`, `task_heatmap.png`, `error_tags.png` |
| `requirements.txt` | Pins exact library versions | When setting up the venv | `pip install -r requirements.txt` | (none) | (installs packages into `.venv/`) |
| `.env.example` | Template for your API key | Once, at setup | `cp .env.example .env && chmod 600 .env` | (none) | `.env` (you paste the key) |
| `.gitignore` | Keeps secrets and throwaway outputs out of Git | Automatically, by Git | (none) | (none) | (none) |

## Full sequence

Free end-to-end test (no API key, no cost):

```bash
python selftest.py
python run_experiment.py --dry-run --repeats 2
python score.py --dry-run
python analyze.py --dry-run
```

Real experiment:

```bash
python run_experiment.py --models haiku --tasks HML --repeats 1   # tiny pilot
python run_experiment.py --repeats 5                               # 320 calls, resumable
python score.py
python analyze.py
```

## Per-file docs

- [01 - ground_truth.py](01-ground_truth.md)
- [02 - make_tasks.py and tasks.json](02-make_tasks-and-tasks-json.md)
- [03 - prompts.py](03-prompts.md)
- [04 - run_experiment.py](04-run_experiment.md)
- [05 - dryrun_mock.py and selftest.py](05-dryrun_mock-and-selftest.md)
- [06 - score.py](06-score.md)
- [07 - analyze.py](07-analyze.md)
- [08 - config files](08-config-files.md)

---

## Part 3: Form Forge (`web/`)

Each model gets only a headless browser and must click through SEC EDGAR to find book equity in filings made Jul–Aug 2026. 8 tasks x 2 conditions (STEPS, GOAL_ONLY) x 4 models x 3 repeats = 192 runs. PASS = exact whole-dollar value and the original filing's accession number.

```mermaid
flowchart TD
    TW["web/tasks_web.json<br/>8 tasks"] --> AK["web/answer_key.py"]
    XBRL["data.sec.gov/api/xbrl<br/>(blocked for the models)"] --> AK
    AK --> KEY["web/answer_key.json<br/>+ data/raw/*.json.gz (sha256)"]
    TW --> PW["web/prompts_web.py"]
    PW --> RW["web/run_web.py<br/>agent loop"]
    RW <--> API["Claude API, tool use<br/>(or mock_agent.py with --dry-run)"]
    RW <--> BT["web/browser_tools.py<br/>headless Chromium, 9 tools"]
    BT <--> SP["web/sec_policy.py<br/>allowlist, robots.txt, 5 req/s, User-Agent"]
    SP <--> SEC["www.sec.gov EDGAR pages<br/>(or web/fixtures with --offline)"]
    RW --> RUNS["runs_web/TASK__COND__MODEL__rK/<br/>steps.jsonl, pages/, final.json"]
    RUNS --> SW["web/score_web.py"]
    KEY --> SW
    SW --> RS["results_web/runs_scored.csv"]
    RS --> AW["web/analyze_web.py"]
    P2["results/runs_scored.csv<br/>(Part 2)"] --> AW
    AW --> OUT["results_web/summary.md, 5 CSVs, 3 figures"]
```

In words:

1. **Answer key.** `answer_key.py` fetched SEC's XBRL data once (11 requests) and froze the exact value, accession and look-alike numbers for each task.
2. **Prompts.** `prompts_web.py` turns a task and condition into the prompt.
3. **Runs.** `run_web.py` loops: the model asks for a tool, `browser_tools.py` runs it in a fresh browser, and the page text goes back. `sec_policy.py` checks and rate-limits every request.
4. **Scoring.** `score_web.py` gives PASS or a tag.
5. **Analysis.** `analyze_web.py` makes the H1–H5 tables, tests, figures and the Part 2 vs Part 3 table.

`mock_agent.py`, `capture_fixtures.py` and `selftest_web.py` test it all for free.

| file | what it does in one line | command | writes |
|---|---|---|---|
| `web/tasks_web.json` | the 8 tasks, STEPS text, schemas, frozen answers | (data file) | (answers written by `answer_key.py`) |
| `web/answer_key.py` | builds and freezes the key | `python web/answer_key.py --check` | `web/answer_key.json`, `web/data/raw/` |
| `web/sec_policy.py` | allow/block, robots.txt, 5 req/s, User-Agent | (imported) | (nothing) |
| `web/browser_tools.py` | browser + 9 tools | (imported) | (nothing) |
| `web/prompts_web.py` | system + task prompt | `python web/prompts_web.py T1 STEPS` | (prints) |
| `web/run_web.py` | the agent loop | `python web/run_web.py --dry-run --tasks T1 T4` | `runs_web*/` |
| `web/mock_agent.py` | fake model, 9 personas | (used by `--dry-run`) | (nothing) |
| `web/capture_fixtures.py` | saves live pages for offline tests | `python web/capture_fixtures.py --all` | `web/fixtures/` |
| `web/selftest_web.py` | 148 offline checks | `python web/selftest_web.py` | (temp folder) |
| `web/score_web.py` | PASS + tags | `python web/score_web.py --runs runs_web` | `results_web/runs_scored.csv` |
| `web/analyze_web.py` | stats and figures | `python web/analyze_web.py --in results_web/runs_scored.csv --part2 results/runs_scored.csv` | `results_web/*` |

Free end-to-end test (no API key):

```bash
python web/answer_key.py --check
python web/selftest_web.py
python web/run_web.py --dry-run --offline --tasks T1 T4 --conds STEPS --repeats 1 --out runs_web_mock/offline
python web/score_web.py --runs runs_web_mock/offline --out results_web_mock/offline
```

Real experiment: see Steps 16–18 of [../03-step-by-step-checklist.md](../03-step-by-step-checklist.md).

Part 3 explainers:

- [09 - answer_key.py and tasks_web.json](09-answer_key-and-tasks_web.md)
- [10 - sec_policy.py](10-sec_policy.md)
- [11 - browser_tools.py](11-browser_tools.md)
- [12 - prompts_web.py](12-prompts_web.md)
- [13 - run_web.py](13-run_web.md)
- [14 - mock_agent.py, capture_fixtures.py, selftest_web.py](14-mock_agent-capture_fixtures-selftest_web.md)
- [15 - score_web.py and analyze_web.py](15-score_web-and-analyze_web.md)
