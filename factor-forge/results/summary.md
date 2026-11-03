# Factor Forge results

Runs scored: 320 (excluded 0 API errors). PASS = script ran, coverage >= 95% of official months, RMSE <= 1 bp vs official series.

## Pass rate by model and condition (Wilson 95% CI)

| model | condition | passed | n | pass_rate | ci |
|---|---|---|---|---|---|
| fable | RECIPE | 40 | 40 | 100 | [91.2, 100.0] |
| fable | NAME_ONLY | 38 | 40 | 95 | [83.5, 98.6] |
| opus | RECIPE | 40 | 40 | 100 | [91.2, 100.0] |
| opus | NAME_ONLY | 39 | 40 | 97.5 | [87.1, 99.6] |
| sonnet | RECIPE | 40 | 40 | 100 | [91.2, 100.0] |
| sonnet | NAME_ONLY | 40 | 40 | 100 | [91.2, 100.0] |
| haiku | RECIPE | 40 | 40 | 100 | [91.2, 100.0] |
| haiku | NAME_ONLY | 39 | 40 | 97.5 | [87.1, 99.6] |

## Fisher exact tests (two-sided; Holm-adjusted p across all rows)

| comparison | a_pass | b_pass | p_value | p_holm |
|---|---|---|---|---|
| RECIPE: fable vs opus | 40/40 | 40/40 | 1 | 1 |
| RECIPE: opus vs sonnet | 40/40 | 40/40 | 1 | 1 |
| RECIPE: sonnet vs haiku | 40/40 | 40/40 | 1 | 1 |
| NAME_ONLY: fable vs opus | 38/40 | 39/40 | 1 | 1 |
| NAME_ONLY: opus vs sonnet | 39/40 | 40/40 | 1 | 1 |
| NAME_ONLY: sonnet vs haiku | 40/40 | 39/40 | 1 | 1 |
| fable: RECIPE vs NAME_ONLY | 40/40 | 38/40 | 0.494 | 1 |
| opus: RECIPE vs NAME_ONLY | 40/40 | 39/40 | 1 | 1 |
| sonnet: RECIPE vs NAME_ONLY | 40/40 | 40/40 | 1 | 1 |
| haiku: RECIPE vs NAME_ONLY | 40/40 | 39/40 | 1 | 1 |

## Cost (USD) and latency

| model | condition | runs | passed | mean_input_tokens | mean_output_tokens | total_cost_usd | cost_per_correct_usd | mean_latency_s | median_latency_s |
|---|---|---|---|---|---|---|---|---|---|
| fable | RECIPE | 40 | 40 | 3254.375 | 937.55 | 3.177 | 0.079 | 9.925 | 9.25 |
| fable | NAME_ONLY | 40 | 38 | 3071 | 1188.55 | 3.606 | 0.095 | 13.287 | 13.375 |
| fable | ALL | 80 | 78 | 3162.688 | 1063.05 | 6.782 | 0.087 | 11.606 | 11.06 |
| opus | RECIPE | 40 | 40 | 3254.375 | 1135.275 | 1.429 | 0.036 | 10.141 | 10.045 |
| opus | NAME_ONLY | 40 | 39 | 3071 | 1381.525 | 1.597 | 0.041 | 12.423 | 12.055 |
| opus | ALL | 80 | 79 | 3162.688 | 1258.4 | 3.026 | 0.038 | 11.282 | 11.045 |
| sonnet | RECIPE | 40 | 40 | 3254.375 | 760.95 | 0.565 | 0.014 | 5.248 | 5.36 |
| sonnet | NAME_ONLY | 40 | 40 | 3071 | 1031.125 | 0.658 | 0.017 | 7.223 | 6.835 |
| sonnet | ALL | 80 | 80 | 3162.688 | 896.038 | 1.223 | 0.015 | 6.235 | 6.105 |
| haiku | RECIPE | 40 | 40 | 3254.375 | 2056.575 | 0.054 | 0.001 | 8.709 | 8.6 |
| haiku | NAME_ONLY | 40 | 39 | 3071 | 2965.575 | 0.072 | 0.002 | 13.194 | 12.75 |
| haiku | ALL | 80 | 79 | 3162.688 | 2511.075 | 0.126 | 0.002 | 10.951 | 10.395 |

## Primary error tags among failed runs

| model_alias | condition | BAD_FORMAT | CRASH | WRONG_FORMULA |
|---|---|---|---|---|
| fable | NAME_ONLY | 2 | 0 | 0 |
| haiku | NAME_ONLY | 0 | 0 | 1 |
| opus | NAME_ONLY | 0 | 1 | 0 |

## Pass rate by task

| task | fable/RECIPE | fable/NAME_ONLY | opus/RECIPE | opus/NAME_ONLY | sonnet/RECIPE | sonnet/NAME_ONLY | haiku/RECIPE | haiku/NAME_ONLY |
|---|---|---|---|---|---|---|---|---|
| CMA | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| HML | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| LT_REV | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| MOM | 1 | 0.6 | 1 | 1 | 1 | 1 | 1 | 1 |
| RMW | 1 | 1 | 1 | 0.8 | 1 | 1 | 1 | 1 |
| SMB_3F | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| SMB_5F | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0.8 |
| ST_REV | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

Caveats: runs of the same task are not independent (task difficulty is shared), so the Fisher tests treat each run as independent and overstate precision; report per-task results alongside. Figures: figures/pass_rate.png, figures/task_heatmap.png, figures/error_tags.png.
