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
| **Book equity (BE)** | What the balance sheet says the company is worth to its shareholders: total stockholders' equity. The "B" in B/M. |
| **Market equity (ME)** | Shares outstanding × share price. The "M" in B/M. |
| **10-Q / 10-K** | A company's quarterly report / annual report to the SEC. The quarter that ends the fiscal year is in the 10-K, not a 10-Q. |
| **10-Q/A** | An amended filing that corrects an earlier one. |
| **Fiscal year / fiscal quarter** | A company's own accounting calendar. Apple's Q3 FY2026 ended June 27, 2026; Walmart's fiscal 2027 started in February 2026. |
| **Comparative column** | The earlier date printed next to the current one on a balance sheet (e.g. last year-end). |
| **Noncontrolling interest (NCI)** | The part of a subsidiary owned by outsiders. "Total equity" may include it; the parent's equity does not. |
| **Preferred stock** | Shares with a fixed claim ahead of common stock. Common book equity = total equity − preferred. |
| **Liquidation preference** | What preferred holders get back if the firm is wound up. It can differ from the preferred stock's balance-sheet value. |
| **Stockholders' deficit** | Negative equity: liabilities exceed assets. Shown in parentheses, e.g. (3,982,431). |
| **"$ in Millions / Thousands"** | The units line at the top of a balance-sheet page. Multiply to get whole dollars. |
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
| **Holm adjustment** | A correction to p-values when you run many tests at once, so one lucky test doesn't look significant. |
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

## SEC EDGAR and web agents (Part 3)

| Term | Plain meaning |
|---|---|
| **SEC** | The US Securities and Exchange Commission. Public companies must file their reports with it. |
| **EDGAR** | The SEC's free website of company filings (www.sec.gov). |
| **CIK** | Central Index Key: the SEC's ID number for a company (Apple = 320193). |
| **Accession number** | The ID of one filing, like `0000320193-26-000020`. Without dashes it is the filing's folder name. |
| **Filing index** | The page listing every document in one filing, with its accession number. |
| **XBRL** | Tags in the filing that label each number by its meaning (e.g. `us-gaap:StockholdersEquity`), so computers can read it. |
| **companyfacts / frames API** | SEC's XBRL data API (`data.sec.gov/api/xbrl`). The answer key comes from it; the models' browser is blocked from it. |
| **R page** | One financial table of a filing rendered as a web page (`R4.htm` = Apple's balance sheet). |
| **FilingSummary.xml** | A filing's table of contents that maps report names to R pages. |
| **robots.txt** | A site's list of paths robots may and may not visit. SEC's forbids `/cgi-bin`, which the harness obeys. |
| **User-Agent** | The line a program sends to say what it is. SEC asks automated tools to declare a name and contact (`SEC_USER_AGENT`). |
| **Fair access / rate limit** | SEC allows at most 10 requests per second; the harness uses at most 5. |
| **HTTP 403** | "Forbidden": the site refused the request. SEC returns it to undeclared robots. |
| **Headless browser** | A real browser (Chromium) running without a window, controlled by code (Playwright). |
| **Playwright** | The Python library that drives the headless browser. |
| **Tool use** | The API feature that lets a model call functions you define (goto, click, ...). The harness runs each call and sends back the result. |
| **Agent loop** | Model asks for a tool → harness runs it → result goes back → repeat, until it answers or hits a limit. |
| **Observation** | The text the model gets back from one tool call: the page's visible text with refs. |
| **Ref** | A label like `[e12 link]` that marks a clickable or typeable element, so the model can say `click(ref="e12")`. |
| **Step cap** | The maximum number of tool calls per run (30, or 50 for T8). |
| **Prompt caching** | The API stores the start of a long conversation so later turns reread it at a fraction of the price. |
| **Effort** | An API setting for how hard the model thinks; `high` for every model here. |
| **Fixtures** | Saved copies of web pages, so tests can run offline. |
| **Persona** | One scripted behavior of the fake model (e.g. `units` always forgets to convert). |
| **Grounded / ungrounded** | Whether the submitted number appeared on a page the model actually saw. |
| **Training cutoff** | The date after which a model has seen no data. All Part 3 filings are after it. |
| **Budget guard** | `--budget-usd`: the runner stops before a run that could push total spend past the cap, and stops mid-run once the real total reaches it. |
