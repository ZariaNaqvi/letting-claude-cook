# 5. Glossary

## Finance

| Term | Plain meaning |
|---|---|
| **Factor** | A long-short strategy written down as a monthly return series. It measures a pattern in stock returns, e.g. "cheap stocks beat expensive stocks." |
| **Long-short** | Buy one group (long), sell another short, and keep the difference. It shows the *spread* between the groups, not the market's overall move. |
| **Fama-French factors** | The standard factors (market, SMB, HML, RMW, CMA), plus momentum and reversal from Ken French's library. Used in nearly every asset-pricing paper. |
| **Book-to-market (B/M)** | Accounting value ÷ market value. High B/M = "cheap" = **value**. Low B/M = "expensive" = **growth**. |
| **Operating profitability (OP)** | Profits relative to book equity. High = robust, low = weak. |
| **Investment (INV)** | How fast a firm's total assets grow. Low = conservative, high = aggressive. |
| **Prior return** | A stock's past return over a window. 12_2 = months t−12 to t−2 (momentum), 1_0 = last month (short-term reversal), 60_13 = months t−60 to t−13 (long-term reversal). |
| **2 × 3 sort** | Split stocks by size (small/big at the NYSE median), then by the characteristic (bottom 30% / middle 40% / top 30%). That gives 6 portfolios. |
| **Value-weighted (VW)** | Portfolio return weights each stock by its market cap. The official factors use VW. |
| **Equal-weighted (EW)** | Every stock counts equally. It is in the same file, and it is the wrong table for these factors. |
| **CRSP** | The Center for Research in Security Prices, the stock database French builds from. "202608 release" = data through August 2026. |
| **Basis point (bp)** | 0.01 percentage points. 1 bp = 0.01%. French's files are in percent, so 1 bp = 0.01 in the file's units. |
| **Anomaly / signal** | Older terms for a characteristic that predicts returns, used in Replication Swarm. |

## Statistics

| Term | Plain meaning |
|---|---|
| **RMSE** | Root-mean-square error: square each month's miss, average them, take the square root. It's the "typical miss" and punishes big misses more. |
| **Max absolute error** | The single worst month's miss. |
| **Correlation** | Whether two series move together (−1 to 1). It can be 1.0 even if one series is 100× the other, which is why RMSE is the main score. |
| **Coverage** | Share of the official months your output includes. |
| **Pass rate** | Passes ÷ attempts, e.g. 34/40 = 85%. |
| **Wilson 95% interval** | A range that probably contains the true pass rate. It works well for small samples and for rates near 0% or 100%. |
| **Fisher exact test** | Tests whether two pass rates (e.g. 36/40 vs. 25/40) differ by more than chance. The p-value is the chance of a gap this big if the models were really equal. |
| **Repeat** | Sending the identical prompt again. Models are not perfectly consistent, so repeats measure a rate. |

## Software and AI

| Term | Plain meaning |
|---|---|
| **API** | A way for your Python code to call a model directly instead of typing in the chat window. Every call is identical and logged. |
| **API key** | A password for the API (`sk-ant-...`). It lives in `.env`. Never commit or share it. |
| **Token** | A chunk of text (about ¾ of a word). You pay per million input and output tokens. |
| **Harness** | The program that runs the experiment: builds the prompt, calls the model, runs the code it returns, and saves everything (`run_experiment.py`). |
| **Dry run** | A rehearsal with a fake model. It costs nothing and tests the pipeline. |
| **Pilot** | A tiny real run (8 calls) to catch problems before spending on 320. |
| **Condition** | One version of the prompt: RECIPE or NAME_ONLY. |
| **Ground truth / answer key** | The official numbers every run is graded against, plus your proof that they can be reproduced. |
| **Contamination** | Anything that lets the tested model see help it wasn't supposed to have, such as your hints or the official answer. |
| **venv** | A Python environment private to this project. Activate it with `source .venv/bin/activate`. |
| **`.env` / `.gitignore`** | `.env` holds secrets. `.gitignore` lists files git must never commit. |
| **git tag** | A permanent named bookmark on a commit (e.g. `prompts-v1`), so you can prove which version produced your results. |
| **Subprocess / timeout** | Running a model's script as a separate program, and killing it if it takes longer than 60 seconds. |
| **Fork / upstream** | Your copy of the course repo on GitHub, and the instructor's original. |
