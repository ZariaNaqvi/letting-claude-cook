# Form Forge (Part 3) results

Runs scored: 192 (excluded 0 HARNESS_ERROR runs). PASS = answered, exact whole-dollar value, original accession (T8: four exact values + exact ranking).

## Part 2 vs Part 3 (the headline table)

| model | part2 | part3 | part2_cost | part3_cost |
|---|---|---|---|---|
| fable | 78/80 | 48/48 | 6.78 | 11.4 |
| opus | 79/80 | 46/48 | 3.03 | 4.65 |
| sonnet | 80/80 | 42/48 | 1.22 | 5.41 |
| haiku | 79/80 | 43/48 | 0.13 | 0.19 |
| ALL | 316/320 | 179/192 | 11.16 | 21.65 |

## Pass rates (Wilson 95% CI)

| grouping | group | passed | n | pass_rate | ci |
|---|---|---|---|---|---|
| overall | all | 179 | 192 | 93.2 | [88.8, 96.0] |
| model | fable | 48 | 48 | 100 | [92.6, 100.0] |
| model | haiku | 43 | 48 | 89.6 | [77.8, 95.5] |
| model | opus | 46 | 48 | 95.8 | [86.0, 98.8] |
| model | sonnet | 42 | 48 | 87.5 | [75.3, 94.1] |
| condition | GOAL_ONLY | 87 | 96 | 90.6 | [83.1, 95.0] |
| condition | STEPS | 92 | 96 | 95.8 | [89.8, 98.4] |
| task | T1 | 24 | 24 | 100 | [86.2, 100.0] |
| task | T2 | 22 | 24 | 91.7 | [74.2, 97.7] |
| task | T3 | 21 | 24 | 87.5 | [69.0, 95.7] |
| task | T4 | 21 | 24 | 87.5 | [69.0, 95.7] |
| task | T5 | 23 | 24 | 95.8 | [79.8, 99.3] |
| task | T6 | 22 | 24 | 91.7 | [74.2, 97.7] |
| task | T7 | 24 | 24 | 100 | [86.2, 100.0] |
| task | T8 | 22 | 24 | 91.7 | [74.2, 97.7] |
| model x condition | fable / GOAL_ONLY | 24 | 24 | 100 | [86.2, 100.0] |
| model x condition | haiku / GOAL_ONLY | 22 | 24 | 91.7 | [74.2, 97.7] |
| model x condition | opus / GOAL_ONLY | 23 | 24 | 95.8 | [79.8, 99.3] |
| model x condition | sonnet / GOAL_ONLY | 18 | 24 | 75 | [55.1, 88.0] |
| model x condition | fable / STEPS | 24 | 24 | 100 | [86.2, 100.0] |
| model x condition | haiku / STEPS | 21 | 24 | 87.5 | [69.0, 95.7] |
| model x condition | opus / STEPS | 23 | 24 | 95.8 | [79.8, 99.3] |
| model x condition | sonnet / STEPS | 24 | 24 | 100 | [86.2, 100.0] |

## Fisher exact tests (two-sided; Holm-adjusted across all rows)

| hypothesis | comparison | a | b | p_value | p_holm |
|---|---|---|---|---|---|
| H1 | all models: Part 2 vs Part 3 | 316/320 | 179/192 | 0.001 | 0.019 |
| H1 | fable: Part 2 vs Part 3 | 78/80 | 48/48 | 0.528 | 1 |
| H1 | opus: Part 2 vs Part 3 | 79/80 | 46/48 | 0.556 | 1 |
| H1 | sonnet: Part 2 vs Part 3 | 80/80 | 42/48 | 0.002 | 0.029 |
| H1 | haiku: Part 2 vs Part 3 | 79/80 | 43/48 | 0.028 | 0.303 |
| H2 | fable vs haiku | 48/48 | 43/48 | 0.056 | 0.56 |
| H2 | opus vs sonnet | 46/48 | 42/48 | 0.268 | 1 |
| H2 | fable vs opus | 48/48 | 46/48 | 0.495 | 1 |
| H2 | sonnet vs haiku | 42/48 | 43/48 | 1 | 1 |
| H3 | all models: STEPS vs GOAL_ONLY | 92/96 | 87/96 | 0.25 | 1 |
| H3 | fable: STEPS vs GOAL_ONLY | 24/24 | 24/24 | 1 | 1 |
| H3 | opus: STEPS vs GOAL_ONLY | 23/24 | 23/24 | 1 | 1 |
| H3 | sonnet: STEPS vs GOAL_ONLY | 24/24 | 18/24 | 0.022 | 0.263 |
| H3 | haiku: STEPS vs GOAL_ONLY | 21/24 | 22/24 | 1 | 1 |

## Error tags among failed runs (H4)

| model_alias | GAVE_UP | STEP_LIMIT | TIME_LIMIT |
|---|---|---|---|
| haiku | 0 | 0 | 5 |
| opus | 0 | 0 | 2 |
| sonnet | 1 | 2 | 3 |

Share of failures that are finance/navigation mistakes (WRONG_LINE, WRONG_PERIOD, UNITS, SIGN, WRONG_ENTITY, WRONG_FILING, NAV_ERROR): 0%

## Efficiency and cost (H5)

| model | runs | passed | median_steps_success | iqr_steps_success | mean_prompt_tokens | mean_output_tokens | cache_read_share | total_cost_usd | cost_per_correct_usd | median_wall_s |
|---|---|---|---|---|---|---|---|---|---|---|
| fable | 48 | 48 | 9 | 1.25 | 79454.229 | 1025.896 | 0.829 | 11.4 | 0.237 | 32.55 |
| opus | 48 | 46 | 9 | 3.75 | 69275.812 | 955.604 | 0.807 | 4.654 | 0.101 | 32.5 |
| sonnet | 48 | 42 | 10 | 3.75 | 174444.771 | 2413.812 | 0.866 | 5.411 | 0.129 | 32.6 |
| haiku | 48 | 43 | 9 | 3 | 104216.854 | 1890.167 | 0.843 | 0.186 | 0.004 | 35.15 |

## Behavior

| model_alias | condition | tried_blocked | used_search_form |
|---|---|---|---|
| fable | GOAL_ONLY | 1 | 0 |
| fable | STEPS | 1 | 1 |
| haiku | GOAL_ONLY | 1 | 0 |
| haiku | STEPS | 0.875 | 1 |
| opus | GOAL_ONLY | 1 | 0 |
| opus | STEPS | 1 | 0.958 |
| sonnet | GOAL_ONLY | 1 | 0 |
| sonnet | STEPS | 1 | 1 |

Caveats: runs of one task share its difficulty, so treating runs as independent overstates precision; report per-task results alongside. The live site can change between runs (new filings); the run order is repeat-major so any change hits all models equally.
