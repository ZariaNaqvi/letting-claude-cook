# Form Forge (Part 3) results

Runs scored: 192 (excluded 0 HARNESS_ERROR runs). PASS = answered, exact whole-dollar value, original accession (T8: four exact values + exact ranking).

## Part 2 vs Part 3 (the headline table)

| model | part2 | part3 | part2_cost | part3_cost |
|---|---|---|---|---|
| fable | 78/80 | 48/48 | 6.78 | 11.4 |
| opus | 79/80 | 48/48 | 3.03 | 4.8 |
| sonnet | 80/80 | 45/48 | 1.22 | 5.56 |
| haiku | 79/80 | 48/48 | 0.13 | 0.2 |
| ALL | 316/320 | 189/192 | 11.16 | 21.96 |

## Pass rates (Wilson 95% CI)

| grouping | group | passed | n | pass_rate | ci |
|---|---|---|---|---|---|
| overall | all | 189 | 192 | 98.4 | [95.5, 99.5] |
| model | fable | 48 | 48 | 100 | [92.6, 100.0] |
| model | haiku | 48 | 48 | 100 | [92.6, 100.0] |
| model | opus | 48 | 48 | 100 | [92.6, 100.0] |
| model | sonnet | 45 | 48 | 93.8 | [83.2, 97.9] |
| condition | GOAL_ONLY | 93 | 96 | 96.9 | [91.2, 98.9] |
| condition | STEPS | 96 | 96 | 100 | [96.2, 100.0] |
| task | T1 | 24 | 24 | 100 | [86.2, 100.0] |
| task | T2 | 24 | 24 | 100 | [86.2, 100.0] |
| task | T3 | 24 | 24 | 100 | [86.2, 100.0] |
| task | T4 | 23 | 24 | 95.8 | [79.8, 99.3] |
| task | T5 | 24 | 24 | 100 | [86.2, 100.0] |
| task | T6 | 22 | 24 | 91.7 | [74.2, 97.7] |
| task | T7 | 24 | 24 | 100 | [86.2, 100.0] |
| task | T8 | 24 | 24 | 100 | [86.2, 100.0] |
| model x condition | fable / GOAL_ONLY | 24 | 24 | 100 | [86.2, 100.0] |
| model x condition | haiku / GOAL_ONLY | 24 | 24 | 100 | [86.2, 100.0] |
| model x condition | opus / GOAL_ONLY | 24 | 24 | 100 | [86.2, 100.0] |
| model x condition | sonnet / GOAL_ONLY | 21 | 24 | 87.5 | [69.0, 95.7] |
| model x condition | fable / STEPS | 24 | 24 | 100 | [86.2, 100.0] |
| model x condition | haiku / STEPS | 24 | 24 | 100 | [86.2, 100.0] |
| model x condition | opus / STEPS | 24 | 24 | 100 | [86.2, 100.0] |
| model x condition | sonnet / STEPS | 24 | 24 | 100 | [86.2, 100.0] |

## Fisher exact tests (two-sided; Holm-adjusted across all rows)

| hypothesis | comparison | a | b | p_value | p_holm |
|---|---|---|---|---|---|
| H1 | all models: Part 2 vs Part 3 | 316/320 | 189/192 | 1 | 1 |
| H1 | fable: Part 2 vs Part 3 | 78/80 | 48/48 | 0.528 | 1 |
| H1 | opus: Part 2 vs Part 3 | 79/80 | 48/48 | 1 | 1 |
| H1 | sonnet: Part 2 vs Part 3 | 80/80 | 45/48 | 0.051 | 0.709 |
| H1 | haiku: Part 2 vs Part 3 | 79/80 | 48/48 | 1 | 1 |
| H2 | fable vs haiku | 48/48 | 48/48 | 1 | 1 |
| H2 | opus vs sonnet | 48/48 | 45/48 | 0.242 | 1 |
| H2 | fable vs opus | 48/48 | 48/48 | 1 | 1 |
| H2 | sonnet vs haiku | 45/48 | 48/48 | 0.242 | 1 |
| H3 | all models: STEPS vs GOAL_ONLY | 96/96 | 93/96 | 0.246 | 1 |
| H3 | fable: STEPS vs GOAL_ONLY | 24/24 | 24/24 | 1 | 1 |
| H3 | opus: STEPS vs GOAL_ONLY | 24/24 | 24/24 | 1 | 1 |
| H3 | sonnet: STEPS vs GOAL_ONLY | 24/24 | 21/24 | 0.234 | 1 |
| H3 | haiku: STEPS vs GOAL_ONLY | 24/24 | 24/24 | 1 | 1 |

## Error tags among failed runs (H4)

| model_alias | GAVE_UP | STEP_LIMIT |
|---|---|---|
| sonnet | 1 | 2 |

Share of failures that are finance/navigation mistakes (WRONG_LINE, WRONG_PERIOD, UNITS, SIGN, WRONG_ENTITY, WRONG_FILING, NAV_ERROR): 0%

## Efficiency and cost (H5)

| model | runs | passed | median_steps_success | iqr_steps_success | mean_prompt_tokens | mean_output_tokens | cache_read_share | total_cost_usd | cost_per_correct_usd | median_wall_s |
|---|---|---|---|---|---|---|---|---|---|---|
| fable | 48 | 48 | 9 | 1.25 | 79454.229 | 1025.896 | 0.829 | 11.4 | 0.237 | 32.55 |
| opus | 48 | 48 | 9 | 3.25 | 71900.979 | 1008.188 | 0.81 | 4.8 | 0.1 | 32.5 |
| sonnet | 48 | 45 | 10 | 4 | 192611.646 | 2544.833 | 0.883 | 5.558 | 0.123 | 31.35 |
| haiku | 48 | 48 | 9 | 3 | 117300.688 | 2122.479 | 0.85 | 0.204 | 0.004 | 33.75 |

## Behavior

| model_alias | condition | tried_blocked | used_search_form |
|---|---|---|---|
| fable | GOAL_ONLY | 1 | 0 |
| fable | STEPS | 1 | 1 |
| haiku | GOAL_ONLY | 1 | 0 |
| haiku | STEPS | 0.917 | 1 |
| opus | GOAL_ONLY | 1 | 0 |
| opus | STEPS | 1 | 0.958 |
| sonnet | GOAL_ONLY | 1 | 0 |
| sonnet | STEPS | 1 | 1 |

Caveats: runs of one task share its difficulty, so treating runs as independent overstates precision; report per-task results alongside. The live site can change between runs (new filings); the run order is repeat-major so any change hits all models equally.
