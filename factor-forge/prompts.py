"""
Factor Forge -- prompt builder.

Builds the exact text sent to every model under test. The SAME function produces
the prompt for every model, so wording never differs across models.

Two conditions:
  RECIPE     -- the prompt states the exact formula and which table to use.
  NAME_ONLY  -- the prompt only names the factor and the files.

Both conditions share the same DATA section (first 60 lines of each raw file,
verbatim) and the same OUTPUT CONTRACT.

FREEZE THIS FILE before the pilot (git tag prompts-v1). Every change after that
must be logged in notes.txt. PROMPT_VERSION is saved in every run's metadata.

Try it:
    python prompts.py HML RECIPE        # prints the prompt
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(HERE, "data", "raw")
TASKS_JSON = os.path.join(HERE, "tasks.json")

PROMPT_VERSION = "v1"
HEAD_LINES = 60                     # how many lines of each file the model sees
CONDITIONS = ["RECIPE", "NAME_ONLY"]

# Software the model's script will run under (keep in sync with requirements.txt)
RUNTIME_NOTE = "Python 3.12, pandas 3.0, numpy 2.x"


def load_tasks():
    """Return (full tasks.json dict, {task_id: task dict})."""
    with open(TASKS_JSON) as fh:
        doc = json.load(fh)
    return doc, {t["id"]: t for t in doc["tasks"]}


def read_lines(path):
    """Split a raw file into lines the same way `wc -l` counts them.

    French files use CRLF line endings and a few contain stray lone '\\r'
    characters. We split on '\\n' only and drop a trailing '\\r', so the line
    count matches `wc -l` and the text shown to the model is the file's text.
    """
    with open(path, "rb") as fh:
        text = fh.read().decode("latin-1")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [ln[:-1] if ln.endswith("\r") else ln for ln in lines]


def file_preview(fname, raw_dir=RAW_DIR, n=HEAD_LINES):
    """First n lines of one raw file + a note saying how much is hidden."""
    lines = read_lines(os.path.join(raw_dir, fname))
    shown = lines[:n]
    rest = len(lines) - len(shown)
    out = [f"=== FILE: {fname} (first {len(shown)} of {len(lines)} lines, verbatim) ==="]
    out += shown
    out.append(f"[file continues; {rest} more lines]" if rest > 0 else "[end of file]")
    return "\n".join(out)


def build_prompt(task, condition, raw_dir=RAW_DIR):
    """Return the full prompt string for one (task, condition)."""
    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {CONDITIONS}")
    files = task["input_files"]

    if condition == "RECIPE":
        task_text = task["recipe_text"] + "\nTABLE TO USE: " + task["block_to_use"]
    else:
        task_text = task["name_only_text"]

    previews = "\n\n".join(file_preview(f, raw_dir) for f in files)

    return f"""TASK
{task_text}

DATA
You are given {len(files)} raw CSV file(s), exactly as downloaded from the Ken French Data Library: {', '.join(files)}.
They are in the current working directory. Below are the first {HEAD_LINES} lines of each file, verbatim.
The files are much longer than what is shown; you have to write code that handles the whole file.

{previews}

OUTPUT CONTRACT
- Reply with exactly ONE Python code block (```python ... ```). I will save it as solution.py and run it unchanged with `python solution.py`, no arguments, from the directory that holds the files.
- The script reads the files above by name from the current directory. No internet access, no other files.
- Allowed libraries: the Python standard library, pandas and numpy only ({RUNTIME_NOTE}).
- The script must write output.csv to the current directory with exactly two columns, in this order: date,value
    date  = integer YYYYMM (for example 192607)
    value = the factor's monthly return in PERCENT (1.23 means 1.23%), same units as the input files
- One row per month, for every month the input data supports. Monthly rows only.
- The script must finish within 60 seconds.
- You may add a short explanation outside the code block; only the code is run and scored.
"""


def prompt_hash(text):
    """Short SHA-256 fingerprint of a prompt (stored in each run's metadata)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


if __name__ == "__main__":
    _, tasks = load_tasks()
    tid = sys.argv[1] if len(sys.argv) > 1 else "HML"
    cond = sys.argv[2] if len(sys.argv) > 2 else "RECIPE"
    p = build_prompt(tasks[tid], cond)
    print(p)
    print(f"\n--- {len(p)} characters, hash {prompt_hash(p)} ---", file=sys.stderr)
