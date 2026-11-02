# 13 - `web/run_web.py`

## In one sentence

It runs every (task, condition, model, repeat): it opens a fresh browser, lets the model call tools until it answers or hits a limit, and saves everything.

## Why it exists

It is Part 3's `run_experiment.py`. Instead of one API call per run, a run is a loop of many calls: the model asks for a tool, the harness runs it in the browser, and the page text goes back.

## How to run it

```bash
# fake model (mock_agent.py), $0
python web/run_web.py --dry-run --tasks T1 T4 --conds STEPS --repeats 1 --out runs_web_mock          # live site
python web/run_web.py --dry-run --offline --tasks all --conds STEPS --repeats 1 --out runs_web_mock/offline   # saved pages only

# real models
python web/run_web.py --pilot --models haiku sonnet --tasks all --conds STEPS GOAL_ONLY --repeats 1 --out runs_web_pilot
caffeinate -i python web/run_web.py --models fable opus sonnet haiku --tasks all --conds STEPS GOAL_ONLY \
       --repeats 3 --effort high --budget-usd 100 --out runs_web 2>&1 | tee -a runlog_web.txt
```

## Flags

| flag | default | meaning |
|---|---|---|
| `--models` | fable opus sonnet haiku | aliases from Part 2's `MODELS` |
| `--tasks` | all | e.g. `T1 T4` or `T1,T4` |
| `--conditions` / `--conds` | STEPS GOAL_ONLY | |
| `--repeats` | 3 | |
| `--dry-run` / `--mock` | off | fake model; no API, no cost |
| `--personas` | all | dry run only |
| `--offline` | off | serve from `web/fixtures/`, no network |
| `--pilot` | off | marks runs as pilot; default `--out runs_web_pilot` |
| `--out` | `runs_web` (`runs_web_mock` for a dry run) | |
| `--effort` | high | |
| `--max-tokens` | 16000 | per API turn |
| `--max-steps` | from the task (30, T8 50) | |
| `--time-limit` | 720 s | |
| `--budget-usd` | 100 | |
| `--api-attempts` | 3 | |
| `--limit` | none | only the first N pending runs |

## What happens before the runs

- Stops if `web/answer_key.json` is missing or T8's market equity isn't frozen.
- User-Agent: `--offline` uses the test value; a dry run accepts the test value; a real run needs your own `SEC_USER_AGENT`.
- A real run loads `ANTHROPIC_API_KEY` from `.env` and stops if it is missing.
- Jobs are in **repeat-major** order (all of r1, then r2, ...), with models interleaved in each cell.
- Finished runs (`final.json` exists) are skipped, except `harness_error` runs, which are redone. A folder holding a dry run can't be reused for a real run, and the other way round.
- Prints `N runs requested, N already done, N to do -> <out>` and appends to `<out>/manifest.json` (argv, models, prices, SDK, Playwright and Python versions).

## One run (`do_run`)

1. Writes `prompt.txt`; builds the tools (8 browser tools + `submit_answer`).
2. `ClaudeCaller` sends: model, `max_tokens`, the system prompt, the tools, the system prompt (with `cache_control` on it; the cache order is tools → system → messages, so this caches both), the messages, a top-level `cache_control` (incremental caching), and `output_config: {effort}`. No temperature, no `tool_choice`, no thinking parameter. Streaming.
3. For each `tool_use`: runs it in the browser, saves `pages/step_NN.txt` and a `steps.jsonl` line, and sends a `tool_result` back.
4. Stops on: `submit_answer` (`answered` or `gave_up`), the step cap (`step_limit`), 12 minutes not counting stalls over 120 s (`time_limit`), no tool call (`no_tool_call`, after up to 2 nudges if the turn hit `max_tokens`), a refusal, 3 site errors or an SEC 403 (`harness_error`).
5. Saves `requests.jsonl`, `transcript.json` and, **last**, `final.json`. (Each API response's cost has already gone to `<out>/spend.jsonl`.)

Bad API key, model ID or parameters stop everything (`FATAL API error`). Other API errors are retried 3 times.

## Cost

`turn_cost` prices each turn from its usage: input at the base price, cache writes at 1.25×, cache reads at 0.025× (Fable), 0.05× (Opus) or 0.10× (Sonnet, Haiku), output at the output price. Haiku has a higher price above 100K prompt tokens. A dry run is priced as Haiku and marked `cost_is_fake`.

**Spend ledger:** every real API response appends its cost to `<out>/spend.jsonl`. The total spent is the sum of that file. Unlike `final.json`, it is never overwritten, so a `harness_error` run that gets redone, or a run cut off by Ctrl-C, still counts.

**Budget guard**, two layers:
1. Before each real run, it adds the total spent to that run's estimated worst case (`worst_case_cost`: every step used, each observation at the 10,800-character cap, about 2K output tokens a turn). If that is over `--budget-usd`, it prints `BUDGET STOP: spent $..., next run could cost up to $..., budget $100.00. N runs not started.` and stops.
2. The estimate is not a hard bound, since one turn may use up to `--max-tokens`. So during a run, before each API call, it checks the real total. Once the budget is reached, the run ends as `harness_error` ("budget reached mid-run"; it is redone on the next resume), the runner prints `BUDGET STOP during ...` and stops. The overshoot is at most one API turn.

## The output line

```
[2/18] T1|STEPS|mock-api|r1   stop=answered steps=12 value=107520000000 accn=0000320193-26-000020 blocked=1 net=39 ...
```

At the end: `done. total real spend in <out>: $X.XX`. If SEC answers 403: `SEC returned HTTP 403 (undeclared automated tool). Stopping ALL runs. Wait at least 10 minutes, check SEC_USER_AGENT, then rerun (resume-safe).`
