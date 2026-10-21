# 08 - Config files: `requirements.txt`, `.env.example`, `.gitignore`

## In one sentence

These three small files say which library versions to install, where your API key goes, and which files Git should never save.

## Why they exist

- **`requirements.txt`** pins exact library versions. The models are told their scripts will run under "Python 3.12, pandas 3.0, numpy 2.x" (see `prompts.py`). If pandas changed halfway through the experiment, some scripts might behave differently, and results would not be comparable.
- **`.env.example`** is a template for your secret API key. The real key goes in `.env`, which is never committed.
- **`.gitignore`** keeps secrets and throwaway files out of the Git repository, and documents which outputs are deliberately kept.

## How to use them

From inside `~/letting-claude-cook/factor-forge`:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env && chmod 600 .env
```

The first line makes a **virtual environment** (`.venv/`), a private folder of Python packages just for this project, activates it (your prompt usually shows `(.venv)`), and installs the pinned versions. The second line copies the key template and makes `.env` readable only by you (`chmod 600`). Then open `.env` in an editor and paste your key.

A successful install ends without errors (pip may print a notice about a newer pip; that is fine). To check:

```bash
python -c "import pandas, anthropic; print(pandas.__version__, anthropic.__version__)"
```

Real output:

```
3.0.6 1.13.0
```

You do not need `.env` for the free tests (`selftest.py` and `--dry-run`).

## Walkthrough

### `requirements.txt`

```
# Factor Forge -- tested 2026-10-14 on Python 3.12 (macOS). anthropic 1.x needs Python >= 3.10.
# The model scripts run with THESE pandas/numpy versions; the prompt tells models "pandas 3.0, numpy 2.x",
# so keep them pinned for the whole experiment.
anthropic==1.13.0
python-dotenv==1.2.4
pandas==3.0.6
numpy==2.5.4
scipy==1.18.1
matplotlib==3.11.2
```

Lines starting with `#` are comments. `==` pins an exact version. What each package is for:

| package | used by | for |
|---|---|---|
| `anthropic` | `run_experiment.py` | calling the Claude API |
| `python-dotenv` | `run_experiment.py` | loading the key from `.env` |
| `pandas` | almost every file, and the models' scripts | tables of returns |
| `numpy` | `ground_truth.py`, `score.py`, `analyze.py`, and the models' scripts | math on arrays |
| `scipy` | `analyze.py` | the Fisher exact test |
| `matplotlib` | `analyze.py` | the figures |

The models' scripts run with the same Python as the harness (`sys.executable`, see doc 04), so they use these exact pandas and numpy versions.

### `.env.example`

```
# Copy this file to .env and paste your key (never commit .env):
#   cp .env.example .env && chmod 600 .env
# Create a key at https://platform.claude.com -> Settings -> API Keys
# (API billing is separate from a claude.ai Pro/Max subscription).
ANTHROPIC_API_KEY=sk-ant-REPLACE-ME
```

A `.env` file holds `NAME=value` lines. `run_experiment.py` calls `load_dotenv(...)`, which reads `.env` and puts `ANTHROPIC_API_KEY` into the environment, where the Anthropic client finds it. The comment points out that API billing is separate from a claude.ai subscription: you need API credit for real runs.

The example file is safe to commit because it holds a placeholder, not a key.

### `.gitignore`

```
# secrets -- never commit
.env

# local Python stuff
.venv/
__pycache__/
*.pyc
.ipynb_checkpoints/
.DS_Store
```

Each line is a pattern Git ignores. `.env` holds your key. `.venv/` is large and can be rebuilt from `requirements.txt`. `__pycache__/` and `*.pyc` are compiled Python files that Python creates automatically (`*` matches anything). `.DS_Store` is a macOS folder file.

```
# dry-run (fake model) outputs: regenerate any time with --dry-run
runs_dryrun/
results_dryrun/
figures_dryrun/

# zips are redundant with data/raw (re-download with the URL pattern in tasks.json)
data/zips/
```

Fake-model outputs are not kept, because they are not real results and can be regenerated. The original zip downloads are skipped because `data/raw/` already holds the extracted CSVs.

```
# COMMITTED on purpose: data/raw, data/truth, data/reference, tasks.json,
# runs/ (every prompt, reply, extracted script and meta.json -- ~15 MB for 320 runs),
# results/ and figures/.
```

This comment explains what is deliberately kept: the input data, the answer files, the task definitions, and every real run (prompt, reply, script, metadata). Keeping all runs means anyone can check or rescore the experiment without paying for API calls again.

## If something goes wrong

- **`ERROR: Could not find a version that satisfies the requirement ...`** - usually your Python is too old or too new for a pinned version. The file was tested on Python 3.12. Check with `python3 --version`.
- **`ModuleNotFoundError: No module named 'pandas'`** when running a script - the venv is not active. Run `source .venv/bin/activate` (you need to do this in every new terminal window).
- **`ANTHROPIC_API_KEY not set`** from `run_experiment.py` - `.env` is missing, still has `REPLACE-ME`, or is not in the project folder. Recheck the `cp` step and paste the key.
- **`git status` shows `.env`** - you are not in the project folder, or `.gitignore` was changed. Do not commit it. If a key was ever committed, delete that key on platform.claude.com and make a new one.

## Check your understanding

1. Why are pandas and numpy pinned to exact versions?
2. Why is `.env.example` committed but `.env` is not?
3. Why are `runs/` and `results/` committed while `runs_dryrun/` is not?

<details>
<summary>Answers</summary>

1. The models' scripts run under these exact versions, and the prompt tells the models which versions to expect. A version change mid-experiment could change how scripts behave and make runs not comparable.
2. `.env.example` holds only a placeholder and shows the format. `.env` holds your real secret key, which must never be shared.
3. `runs/` and `results/` are the real experiment, which cost money and should be checkable by others. Dry-run folders are fake data that can be regenerated for free.

</details>
