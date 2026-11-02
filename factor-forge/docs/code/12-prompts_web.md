# 12 - `web/prompts_web.py`

## In one sentence

It builds the exact system prompt and task prompt for each task and condition, identical for every model.

## Why it exists

Like `prompts.py` in Part 2, it is the experiment's "treatment". If the wording differed across models, you couldn't compare them.

## How to run it

```bash
python web/prompts_web.py T1 STEPS
python web/prompts_web.py T1 GOAL_ONLY
python web/prompts_web.py T8 STEPS
```

It prints `=== SYSTEM ===` and `=== USER ===`. Read a few before the pilot.

## The two conditions

| | STEPS (like RECIPE) | GOAL_ONLY (like NAME_ONLY) |
|---|---|---|
| goal text | yes | yes |
| general rules (whole USD, accession, period_end, step cap) | yes | yes |
| numbered click path, row and column names | yes | no |
| units hint ("$ in Millions: multiply by 1,000,000") | yes | no |
| T8 market-equity values | yes | yes |

Neither prompt mentions the XBRL API.

## The system prompt

Same for every task, model and condition. It says: use only SEC EDGAR, some URLs are blocked, report exactly what the filing shows, call `submit_answer` (or `give_up=true`). It then explains the refs, chunks, `read_page(page=n)` and `find_text`.

## Functions

- `load_tasks()` reads `tasks_web.json`.
- `build_prompt(task, condition, doc)` makes the user message.
- `answer_schema(doc, task)` picks the T1–T7 or T8 schema.
- `prompt_hash(...)` gives the 16-character hash saved in each run's `final.json` (`prompt_sha`).

## Freezing

`PROMPT_VERSION` is `"web-v1-draft"`. After the hand walk and `capture_fixtures.py --all` (Step 14), change it to `"web-v1"`, commit, and tag `prompts-web-v1`. Every later change goes in `notes.txt`. No prompt changes after the main run starts.
