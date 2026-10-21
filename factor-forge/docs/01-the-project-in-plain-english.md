# 1. The project in plain English

## The one-sentence version

You give four Claude models the same messy finance data files and ask each one to rebuild a famous stock-market return series. Because the correct answer is published, you can grade every attempt automatically, down to a hundredth of a percent.

## The pieces, one at a time

### What is a "factor"?

A factor is a simple investing strategy, written down as a monthly return. The classic example is **value**: buy cheap stocks, short expensive stocks, and record how much that position made or lost each month.

Eugene Fama and Kenneth French made a handful of these famous. Every finance class and quant fund uses them. Their returns since 1926 are free on Ken French's website.

The 8 factors in this project:

| Factor | What the strategy bets on | Plain meaning |
|---|---|---|
| **HML** (High Minus Low) | Value | Cheap stocks (high book-to-market) beat expensive ones |
| **SMB** (Small Minus Big) | Size | Small companies beat big ones |
| **RMW** (Robust Minus Weak) | Profitability | Very profitable firms beat weakly profitable ones |
| **CMA** (Conservative Minus Aggressive) | Investment | Firms that invest little beat firms that grow assets fast |
| **MOM** (Momentum) | Trend | Last year's winners keep winning for a while |
| **ST_REV** (Short-term reversal) | Bounce-back | Last month's losers bounce back next month |
| **LT_REV** (Long-term reversal) | Mean reversion | Losers of the past 5 years recover |

SMB appears twice (SMB_3F and SMB_5F) because French computes it differently in his 3-factor and 5-factor files. That difference is one of the traps.

### How is a factor built?

French sorts all US stocks into a 2 × 3 grid: **small or big** company, then **low, middle or high** on the characteristic. That gives 6 portfolios, and he publishes each one's monthly return.

A factor is plain arithmetic on those 6 numbers. For HML:

```
HML = ½ (Small Value + Big Value) − ½ (Small Growth + Big Growth)
```

In words, take the average of the two cheap-stock portfolios and subtract the average of the two expensive-stock portfolios. Averaging small and big separately keeps the size effect out of the value number.

### So what is hard about it?

The arithmetic is easy. **Reading the files is not.** French's CSV files are made for humans, not computers:

- One file holds about 10 tables stacked on top of each other: value-weighted monthly, equal-weighted monthly, annual versions, number of firms, average firm size, and more.
- Several of those tables have **identical column headers**, so code that grabs "the first table that looks right" can silently take the wrong one.
- Annual rows (`1927`) sit in the same file as monthly rows (`192701`).
- Some rows have the wrong number of commas, a few lines have stray carriage-return characters, and the header line falls on a different line number in different files.
- The sign convention changes. Momentum is winners minus losers, but the two reversal factors are losers minus winners.

The model only sees **the first 60 lines** of each file. It has to write code that handles the rest without seeing it, the way you would with a file too big to read.

### What do the models actually do?

For each task, a model gets a prompt with the file previews and one of two instructions:

- **RECIPE:** "Here is the exact formula and which table to use. Write a Python script that builds it."
- **NAME_ONLY:** "Build HML exactly as Ken French does." The model has to know the recipe itself.

The model replies with a Python script. Your harness runs that script on the real files and collects its `output.csv`.

### How do you grade it?

You compare the model's monthly numbers with French's official numbers, month by month. You did this yourself first, in Week 1. Your own correct code matches the official series within **0.28 to 0.42 basis points** (a basis point, or bp, is 0.01 percentage points). The only difference is rounding.

So a run **passes** if:
1. the script ran,
2. it produced at least 95% of the official months, and
3. its RMSE (typical error per month) is **1 bp or less**.

Wrong answers are not close calls. Using the wrong table gives about 137 bp of error, swapping the two SMB definitions gives about 60 bp, and flipping a sign gives 700 to 950 bp. The gap between right and wrong is very wide.

## Why this is an upgrade of Replication Swarm

In Replication Swarm, every model got pre-split decile files, so the job was to subtract two columns. Haiku, Sonnet and Opus all scored the same correlation (0.945), and the score couldn't tell them apart. Your notes found that Haiku got the right number for the wrong reasons.

Factor Forge fixes that in three ways:

| Problem in Replication Swarm | Fix in Factor Forge |
|---|---|
| Task too easy, everyone tied | Raw files with real traps, so the models must parse and reason |
| Correlation tops out around 0.945, so there is no clear "right" | Official answer reproducible to under 1 bp, so pass/fail is sharp |
| Chats run by hand, one per model | An automated harness runs 320 identical, logged API calls |
| Right number, wrong reasons went undetected | Automatic error tags say *how* each failure happened |

## What you will have at the end (target: Nov 11)

1. A GitHub folder with the code, the raw data, all 320 model responses and the scored results, so anyone can reproduce the study.
2. Figures: pass rate by model and condition, a per-factor heatmap, and an error breakdown.
3. A 4–6 page write-up.
4. A 10-minute talk.
5. A resume bullet like: *"Built an automated benchmark that tested 4 Claude models on rebuilding the Fama-French factors from raw data (320 runs, scored to 1 bp)."*

Next: [02 — Goal, hypotheses and scoring](02-goal-hypotheses-and-scoring.md)
