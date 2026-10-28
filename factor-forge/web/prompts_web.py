"""
Form Forge -- prompt builder (system prompt + task prompt).

The SAME functions build the prompt for every model, so wording never differs
across models. Two conditions, mirroring Part 2:

  STEPS      (like RECIPE)    goal + numbered click path + exact row/column + units hint
  GOAL_ONLY  (like NAME_ONLY) goal + general rules only: no site map, no row names, no units hint

Both conditions get the same system prompt, the same tools and the same limits.
Neither prompt mentions the XBRL APIs.

FREEZE THIS FILE before the pilot: set PROMPT_VERSION = "web-v1" after the hand
walk of the STEPS paths (Oct 29). Every change after that goes in notes.txt.

Try it:
    python web/prompts_web.py T1 STEPS
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS_JSON = os.path.join(HERE, "tasks_web.json")

PROMPT_VERSION = "web-v1-draft"
CONDITIONS = ["STEPS", "GOAL_ONLY"]

SYSTEM_PROMPT = (
    "You are a research assistant using a web browser through tools. Data may only be collected "
    "through the SEC EDGAR website (www.sec.gov). Some URLs are blocked. Report exactly what the "
    "filing shows; do not estimate. When you are certain, call submit_answer. If you cannot find it, "
    "call submit_answer with give_up=true.\n\n"
    "How the browser works: each observation shows the page's visible text. Clickable and typeable "
    "elements are marked inline like [e12 link] or [e3 textbox \"Company name\" value=\"\"]. Use those "
    "refs with click, fill and select_option; use only refs from the latest observation. Long pages "
    "are split into chunks: use read_page(page=n) or find_text(query). You have a limited number of "
    "tool calls, stated in the task."
)


RANK_RULES = [
    "Give each book equity as a whole number of US dollars (not millions or thousands).",
    "Book equity means the parent company's total stockholders' (shareholders') equity line "
    "(excluding noncontrolling interests).",
    "Give the ranking as a list of the four tickers, highest B/M first.",
]


def load_tasks():
    """Return (full tasks_web.json dict, {task_id: task dict})."""
    with open(TASKS_JSON) as fh:
        doc = json.load(fh)
    return doc, {t["id"]: t for t in doc["tasks"]}


def answer_schema(doc, task):
    return doc["rank_schema"] if task["kind"] == "rank" else doc["single_schema"]


def _me_block(task):
    me = task["market_equity"]["usd"]
    if not me:
        return "MARKET EQUITY (ME): (not yet frozen -- run web/answer_key.py)"
    lines = [f"  {tic}: ${v:,}" for tic, v in me.items()]
    return "MARKET EQUITY (ME) to use, in US dollars, as of June 30, 2026:\n" + "\n".join(lines)


def build_prompt(task, condition, doc):
    """The user message for one task and condition (the system prompt is SYSTEM_PROMPT)."""
    assert condition in CONDITIONS, condition
    parts = [f"TASK {task['id']}", "", task["goal"], ""]
    if task["kind"] == "rank":
        parts += [_me_block(task), ""]
    rules = doc["general_rules"] if task["kind"] != "rank" else RANK_RULES
    parts += ["RULES:"] + [f"- {r}" for r in rules]
    parts += [f"- You may use at most {task['max_steps']} tool calls in total, including submit_answer.", ""]
    if condition == "STEPS":
        parts += ["STEPS (a click path that works):"]
        parts += [f"{i}. {s}" for i, s in enumerate(task["steps"], 1)]
        parts += [f"Units: {task['units_hint']}", ""]
    parts += ["When you have the answer, call submit_answer."]
    return "\n".join(parts)


def prompt_hash(*texts):
    h = hashlib.sha256()
    for t in texts:
        h.update(t.encode())
    return h.hexdigest()[:16]


if __name__ == "__main__":
    doc, tasks = load_tasks()
    tid = sys.argv[1] if len(sys.argv) > 1 else "T1"
    cond = sys.argv[2] if len(sys.argv) > 2 else "STEPS"
    print("=== SYSTEM ===\n" + SYSTEM_PROMPT + "\n\n=== USER ===\n" + build_prompt(tasks[tid], cond, doc))
