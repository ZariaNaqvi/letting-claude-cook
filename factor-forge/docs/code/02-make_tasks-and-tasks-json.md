# 02 - `make_tasks.py` and `tasks.json`

## In one sentence

`make_tasks.py` writes `tasks.json`, the single file that defines the 8 tasks (inputs, prompt text, answer files) and the pass rule every other script uses.

## Why it exists

Every later step needs the same facts about each task: which raw files the model gets, what the RECIPE prompt says, what the NAME_ONLY prompt says, where the official answer lives, and what counts as a pass. Putting all of that in one JSON file means `prompts.py`, `run_experiment.py`, `score.py`, `analyze.py` and `selftest.py` all read the same definitions. Nothing is typed twice, so nothing can drift out of sync.

`make_tasks.py` also sets the pass threshold from real evidence: it reads the human reference errors from `data/ground_truth_results.csv` (made by `ground_truth.py`) and builds the rule from them.

**JSON** ("JavaScript Object Notation") is a plain-text format for nested data: `{...}` is a dictionary, `[...]` is a list. Python's `json` module reads it into dicts and lists.

## How to run it

Run `ground_truth.py` first (it writes the CSV this script reads). Then, from inside `~/letting-claude-cook/factor-forge` with the venv active:

```bash
python make_tasks.py .
```

The `.` is required. It is the project folder ("this folder"). The script reads `./data/ground_truth_results.csv` and writes `./tasks.json`.

Successful output is one line (real output):

```
tasks ['HML', 'SMB_3F', 'SMB_5F', 'RMW', 'CMA', 'MOM', 'ST_REV', 'LT_REV'] threshold 1.0
```

Rerunning it with the same data produces a byte-identical `tasks.json` (checked with `diff`). You normally run it once. After the prompts are frozen, do not change `tasks.json`, because the task text is part of the prompt.

## Walkthrough of `make_tasks.py`

### Setup

```python
import json, sys, os, pandas as pd
B = sys.argv[1]
res = pd.read_csv(os.path.join(B, "data/ground_truth_results.csv")).set_index("task")
```

`sys.argv` is the list of words you typed on the command line. `sys.argv[0]` is the script name, `sys.argv[1]` is the first argument (the `.`). This is the simplest way to take an argument, without argparse.

`pd.read_csv` loads the human-reference table. `.set_index("task")` makes the task id the row label, so `res.loc["HML"]` gets the HML row.

### Shared text

```python
VW = "Block 0 of each portfolio file: 'Average Value Weighted Returns -- Monthly' (the FIRST table; monthly rows dated YYYYMM). Do NOT use the equal-weighted, annual, number-of-firms, market-cap/firm-size, or characteristic blocks."
OUT = "Write output.csv with columns date (int YYYYMM) and value (monthly return in percent, same units as the input files), one row per month for every month available in the input."
```

`VW` tells the model which table to use (only in the RECIPE condition). `OUT` is the output instruction added to both conditions.

### `t(...)` - build one task

```python
def t(id_, name, off_file, off_col, inputs, recipe, block_note=VW):
    r = res.loc[id_]
    return dict(id=id_, factor_name=name, official_file=off_file, official_column=off_col,
```

One call builds one task dictionary. The parameter is `id_` with an underscore because `id` is already a built-in Python function. Key fields:

```python
                input_files=inputs, block_to_use=block_note, recipe_text=recipe + " " + OUT,
                name_only_text=f"Construct the Fama-French {name} factor exactly as Ken French does, monthly, from the raw files provided ({', '.join(inputs)}). " + OUT,
```

- `recipe_text` - the full formula plus the output instruction. Used in the RECIPE condition.
- `name_only_text` - only the factor's name and the file names. Used in the NAME_ONLY condition. This tests whether the model already knows how French builds the factor.
- `f"..."` is an **f-string**: anything inside `{}` is evaluated and inserted. `', '.join(inputs)` joins a list into one string with commas.

```python
                truth_csv=f"data/truth/{id_}.csv", reference_csv=f"data/reference/{id_}.csv",
                months=int(r.months), first=int(r["first"]), last=int(r["last"]),
                reference_rmse_bp=round(float(r.rmse_bp),4), reference_max_abs_bp=round(float(r.max_abs_bp),4))
```

Where the answer files are, and the human reference results copied from the CSV. (`r["first"]` uses brackets because `first` is also a pandas method name, so `r.first` would not give the column.)

### The 8 tasks

```python
 t("HML","HML (high minus low, value) from the 3-factor model","F-F_Research_Data_Factors.csv","HML",["6_Portfolios_2x3.csv"],
   "HML = 1/2 (Small Value + Big Value) - 1/2 (Small Growth + Big Growth), i.e. 0.5*(SMALL HiBM + BIG HiBM) - 0.5*(SMALL LoBM + BIG LoBM), using the value-weighted monthly returns table (first table) of 6_Portfolios_2x3.csv."),
```

Each task line gives the id, a human name, the official file and column (the answer), the input files the model gets, and the recipe in words and in column names. The recipes match `ground_truth.py` exactly (see doc 01 for the finance meaning). The two reversal tasks add "Note the sign: LOW minus HIGH." to the RECIPE text. SMB_5F tells the model to use only months present in all three files (196307 onward).

### The pass rule

```python
worst = max(x["reference_rmse_bp"] for x in tasks)
```

The worst human-reference RMSE across the 8 tasks. That is LT_REV at 0.4182 bp.

```python
  pass_rule=dict(script_ran=True, min_coverage=0.95, rmse_bp_max=max(1.0, round(2*worst, 2)),
```

The rule: the script must run, must cover at least 95% of official months, and RMSE must be at most `max(1.0, 2 x worst)`. Here 2 x 0.4182 = 0.84, so the threshold is 1.0 bp. The idea: a correct recipe should land within about twice the rounding noise a human gets, and never be held to a bar tighter than 1 bp. A wrong recipe (like the SMB swap, about 60 bp) is far outside.

### Safety lists and output

```python
  never_give_model=["F-F_Research_Data_Factors.csv","F-F_Research_Data_5_Factors_2x3.csv","F-F_Momentum_Factor.csv","F-F_ST_Reversal_Factor.csv","F-F_LT_Reversal_Factor.csv"],
  dropped=[dict(id="HML_5F", reason="Official HML in the 5-factor file is byte-identical to the 3-factor HML over 196307-202608 (max diff 0.00); redundant with HML.")],
```

`never_give_model` lists the official answer files. `run_experiment.py` checks that none of them appear in any task's `input_files`. `dropped` records a task that was considered and removed, with the reason.

```python
json.dump(doc, open(os.path.join(B, "tasks.json"), "w"), indent=2)
print("tasks", [x["id"] for x in tasks], "threshold", doc["pass_rule"]["rmse_bp_max"])
```

`json.dump` writes the dictionary to `tasks.json`. `indent=2` makes it readable.

## What `tasks.json` looks like

Top level (real excerpt):

```json
  "pass_rule": {
    "script_ran": true,
    "min_coverage": 0.95,
    "rmse_bp_max": 1.0,
    "note": "worst human-reference RMSE = 0.4182 bp (inputs rounded to 2 dp for Prior files, 4 dp for 2x3 files; official factors rounded to 2 dp). Threshold = max(1 bp, 2 x worst reference RMSE)."
  },
```

One task (real excerpt, long text fields shortened here with `...`):

```json
    {
      "id": "HML",
      "official_file": "F-F_Research_Data_Factors.csv",
      "official_column": "HML",
      "input_files": [
        "6_Portfolios_2x3.csv"
      ],
      "recipe_text": "HML = 1/2 (Small Value + Big Value) - 1/2 (Small Growth + Big Growth), ...",
      "name_only_text": "Construct the Fama-French HML (high minus low, value) from the 3-factor model factor exactly as Ken French does, monthly, ...",
      "truth_csv": "data/truth/HML.csv",
      "months": 1202,
      "first": 192607,
      "last": 202608,
      "reference_rmse_bp": 0.2908,
      "reference_max_abs_bp": 0.5
    },
```

Months per task: HML and SMB_3F 1202 (from 192607), SMB_5F, RMW and CMA 758 (from 196307), MOM 1196 (from 192701), ST_REV 1207 (from 192602), LT_REV 1148 (from 193101). All end at 202608.

Who reads which fields:

| field | read by |
|---|---|
| `input_files` | `prompts.py` (previews), `run_experiment.py` (copies into the temp folder) |
| `recipe_text`, `block_to_use`, `name_only_text` | `prompts.py` |
| `truth_csv` | `score.py` |
| `pass_rule` | `score.py`, `selftest.py` |
| `never_give_model` | `run_experiment.py` (safety check) |
| task order | `analyze.py` (row order in the heatmap) |

## If something goes wrong

- **`IndexError: list index out of range`** - you ran `python make_tasks.py` without the folder argument. Add ` .` at the end.
- **`FileNotFoundError: ... data/ground_truth_results.csv`** - run `python -I ground_truth.py` first.
- **`KeyError: 'HML'`** - the results CSV does not contain that task, probably because `ground_truth.py` was edited or failed partway. Rerun it and check its printed table.
- **Threshold is not 1.0** - one of the human reference RMSEs got bigger than 0.5 bp. That usually means mismatched data downloads. Check `ground_truth.py`'s output before going on.

## Check your understanding

1. What is the only difference between what a model is told in RECIPE vs NAME_ONLY?
2. How is the 1.0 bp threshold computed?
3. Why is `tasks.json` a separate file instead of being typed into each script?

<details>
<summary>Answers</summary>

1. RECIPE gets `recipe_text` (the exact formula and column names) plus `block_to_use` (which table). NAME_ONLY gets only the factor's name and the file names. Both get the same output instruction and the same file previews.
2. `max(1.0, round(2 * worst, 2))`, where `worst` is the largest human-reference RMSE (0.4182 bp). 2 x 0.4182 = 0.84, which is below 1.0, so the threshold is 1.0 bp.
3. So every script reads the same task definitions. If the recipe or the answer path were typed in several places, they could disagree.

</details>
