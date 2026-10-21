# 03 - `prompts.py`

## In one sentence

`prompts.py` builds the exact text sent to a model for one task and one condition (RECIPE or NAME_ONLY), and gives each prompt a short fingerprint (hash).

## Why it exists

A fair comparison needs every model to get the identical question. One function, `build_prompt`, makes the prompt for every model, so the wording can never differ between Fable, Opus, Sonnet and Haiku. The only thing that changes is the task and the condition.

The prompt has three parts:

1. **TASK** - the recipe (RECIPE) or just the factor name (NAME_ONLY).
2. **DATA** - the first 60 lines of each raw input file, copied verbatim. The model never sees the rest of the file, so it has to write code that finds the right table on its own.
3. **OUTPUT CONTRACT** - the rules: one Python code block, read files from the current folder, only standard library + pandas + numpy, write `output.csv` with `date,value`, finish in 60 seconds.

The file's docstring says to freeze it before the pilot (git tag `prompts-v1`) and log any later change. `PROMPT_VERSION` and the prompt hash are saved with every run, so you can always prove which prompt a run used.

## How to run it

From inside `~/letting-claude-cook/factor-forge` with the venv active:

```bash
python prompts.py HML RECIPE
```

Arguments are the task id and the condition. Both are optional (defaults `HML` and `RECIPE`). This prints the prompt and calls no API. Real output, shortened in the middle:

```
TASK
HML = 1/2 (Small Value + Big Value) - 1/2 (Small Growth + Big Growth), i.e. 0.5*(SMALL HiBM + BIG HiBM) - 0.5*(SMALL LoBM + BIG LoBM), using the value-weighted monthly returns table (first table) of 6_Portfolios_2x3.csv. Write output.csv with columns date (int YYYYMM) and value (monthly return in percent, same units as the input files), one row per month for every month available in the input.
TABLE TO USE: Block 0 of each portfolio file: 'Average Value Weighted Returns -- Monthly' (the FIRST table; monthly rows dated YYYYMM). Do NOT use the equal-weighted, annual, number-of-firms, market-cap/firm-size, or characteristic blocks.

DATA
You are given 1 raw CSV file(s), exactly as downloaded from the Ken French Data Library: 6_Portfolios_2x3.csv.
They are in the current working directory. Below are the first 60 lines of each file, verbatim.
The files are much longer than what is shown; you have to write code that handles the whole file.

=== FILE: 6_Portfolios_2x3.csv (first 60 of 8980 lines, verbatim) ===
This file was created using the 202608 CRSP database.
...
193002,   1.7589,   1.0717,   4.5687,   3.4688,   1.8817,   1.2148
[file continues; 8920 more lines]

OUTPUT CONTRACT
- Reply with exactly ONE Python code block (```python ... ```). I will save it as solution.py and run it unchanged with `python solution.py`, no arguments, from the directory that holds the files.
...
- The script must finish within 60 seconds.
- You may add a short explanation outside the code block; only the code is run and scored.

--- 5549 characters, hash af9b1d9c02cdcb31 ---
```

The last line goes to stderr (the error stream), so if you save the prompt with `python prompts.py HML RECIPE > p.txt`, the file holds only the prompt and the hash line still shows in the terminal.

Try `python prompts.py ST_REV NAME_ONLY` to see how much shorter the NAME_ONLY task text is.

## Walkthrough

### Constants

```python
PROMPT_VERSION = "v1"
HEAD_LINES = 60                     # how many lines of each file the model sees
CONDITIONS = ["RECIPE", "NAME_ONLY"]

# Software the model's script will run under (keep in sync with requirements.txt)
RUNTIME_NOTE = "Python 3.12, pandas 3.0, numpy 2.x"
```

`HEAD_LINES = 60` is a design choice. In `6_Portfolios_2x3.csv`, 60 lines show the preamble, the block-0 title, the header and about 44 months of data. They do not show the other nine tables further down. The model has to guess (or know) the file layout. `RUNTIME_NOTE` tells the model which library versions its script will run under. It must match `requirements.txt`.

### `load_tasks()`

```python
def load_tasks():
    """Return (full tasks.json dict, {task_id: task dict})."""
    with open(TASKS_JSON) as fh:
        doc = json.load(fh)
    return doc, {t["id"]: t for t in doc["tasks"]}
```

Reads `tasks.json`. Returns two things: the whole document, and a dictionary from task id to task. `{t["id"]: t for t in ...}` is a **dict comprehension**, the dictionary version of a list comprehension. A `with open(...) as fh:` block closes the file automatically when done.

### `read_lines(path)`

```python
    with open(path, "rb") as fh:
        text = fh.read().decode("latin-1")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [ln[:-1] if ln.endswith("\r") else ln for ln in lines]
```

Same idea as in `ground_truth.py`: read bytes, split on `\n` only. Here it removes only a trailing `\r` at the end of each line (Windows line ending), so the text shown to the model stays as close to the file as possible, and the line count matches what the Unix command `wc -l` reports. The empty string after the final newline is dropped with `.pop()`.

### `file_preview(fname, raw_dir=RAW_DIR, n=HEAD_LINES)`

```python
    lines = read_lines(os.path.join(raw_dir, fname))
    shown = lines[:n]
    rest = len(lines) - len(shown)
    out = [f"=== FILE: {fname} (first {len(shown)} of {len(lines)} lines, verbatim) ==="]
    out += shown
    out.append(f"[file continues; {rest} more lines]" if rest > 0 else "[end of file]")
    return "\n".join(out)
```

Builds one file's preview: a banner line, the first 60 lines, and a note saying how many lines are hidden. `lines[:n]` is **slicing**: the first `n` items. The `x if condition else y` form is Python's one-line if/else. Telling the model the true length (8980 lines) is a hint that the file holds much more than one table.

### `build_prompt(task, condition, raw_dir=RAW_DIR)`

```python
    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {CONDITIONS}")
    files = task["input_files"]

    if condition == "RECIPE":
        task_text = task["recipe_text"] + "\nTABLE TO USE: " + task["block_to_use"]
    else:
        task_text = task["name_only_text"]
```

This is the only place the two conditions differ. RECIPE gets the formula plus the table instruction. NAME_ONLY gets only the name.

```python
    previews = "\n\n".join(file_preview(f, raw_dir) for f in files)
```

One preview per input file, separated by blank lines. SMB_5F has three input files, so its prompt has three previews and is longer.

The rest of the function is one big f-string with the three sections (TASK, DATA, OUTPUT CONTRACT). A triple-quoted string `"""..."""` can span many lines. Note the output contract explains units ("1.23 means 1.23%"), the date format (`192607`) and "Monthly rows only". The scorer checks each of these.

### `prompt_hash(text)`

```python
def prompt_hash(text):
    """Short SHA-256 fingerprint of a prompt (stored in each run's metadata)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
```

**SHA-256** is a hash function: it turns any text into a fixed-length code. Change even one character and the code changes completely. The first 16 hex characters are kept. Every run stores this in `meta.json` as `prompt_sha`. If two runs of the same task and condition have the same hash, they got exactly the same prompt.

### Running the file directly

```python
if __name__ == "__main__":
    _, tasks = load_tasks()
    tid = sys.argv[1] if len(sys.argv) > 1 else "HML"
    cond = sys.argv[2] if len(sys.argv) > 2 else "RECIPE"
```

`_` is a Python convention for "a value I am ignoring" (here the full tasks document). The rest prints the prompt and, to stderr, its length and hash.

## If something goes wrong

- **`KeyError: 'XYZ'`** - the task id is wrong. Valid ids: `HML SMB_3F SMB_5F RMW CMA MOM ST_REV LT_REV` (upper case).
- **`ValueError: condition must be one of ['RECIPE', 'NAME_ONLY']`** - check the spelling and case of the condition.
- **`FileNotFoundError`** for `tasks.json` or a raw CSV - run from the project folder, and make sure `make_tasks.py` has been run and `data/raw/` is filled.
- **The hash changed between two days** - something in the prompt changed: this file, `tasks.json`, or a raw file's first 60 lines. Find out which before running more trials, because runs with different hashes are not the same experiment.

## Check your understanding

1. Why does the model only see 60 lines of each file?
2. What does the prompt hash let you prove later?
3. Which part of the prompt differs between RECIPE and NAME_ONLY?

<details>
<summary>Answers</summary>

1. That is part of the test. The full files hold about ten stacked tables. Seeing only the top forces the model to write code that finds and stops at the right table, not to copy numbers.
2. That a run used exactly a given prompt. Any change, even one character, gives a different hash.
3. Only the TASK section. RECIPE has the formula and the TABLE TO USE line. NAME_ONLY has just the factor name and files. DATA and OUTPUT CONTRACT are identical.

</details>
