# Factor Forge: class script

## One-liner
"I'm testing whether AI models can take a messy finance data file and calculate a famous number from it exactly right. I already know the correct answer for every month since 1926, so I can grade every attempt automatically."

## Why this matters
"People are starting to use AI for real data analysis in finance: hedge funds, banks, research. The dangerous failure is not a crash, because you notice a crash. It's a number that looks reasonable but is wrong.

Most AI tests check whether a model can answer a question. I'm checking whether it can do an analyst's job: open a messy file, pull out the right table, apply the right formula and get the exact number. Because I have the official answer, I can count exactly how often each model gets fooled, and why."

## What I'm testing (with an example)
"The example is the **value factor**, called HML for 'High Minus Low.' Each month it measures how much cheap stocks beat expensive stocks.

Ken French, a finance professor at Dartmouth, sorts all US stocks into 6 groups: small or big company, crossed with cheap, middle or expensive. He publishes each group's monthly return. The value factor is:

  HML = ½ (Small cheap + Big cheap) − ½ (Small expensive + Big expensive)

So you take four columns, average two, average the other two and subtract.

French publishes the raw file *and* the official HML for every month from July 1926 to August 2026. That's 1,202 months, so I have an answer key.

Here's one test:
1. I send the model a prompt through the Anthropic API. The prompt has the first 60 lines of each data file and the task: write a Python script that calculates HML and saves it as a CSV.
2. The model replies with a script.
3. My program runs that script on the full files, with a 60-second limit.
4. I compare its output with the official numbers, month by month."

## The four things I'm testing the models on
1. **Does it notice the trap in the file?**
   "The file `6_Portfolios_2x3.csv` is over 8,000 lines long and holds 10 tables stacked on top of each other. The right table, value-weighted monthly returns, runs from line 16 to line 1218. At line 1222, the equal-weighted version starts, with **the exact same column names**. The model only sees the first 60 lines, so it never sees the second table. It has to expect that one might be there. If its code grabs the wrong table, the answer is off by 1.37 percentage points a month on average. It still correlates 0.93 with the real answer, and there's no error message."

2. **Does it write code that survives the parts it can't see?**
   "The model writes its code in one shot and never gets to run or test it. The rest of the file has more problems:
   - annual rows like `1927` sitting in the same file as monthly rows like `192701`
   - rows with extra commas that crash a normal `pd.read_csv`
   - invisible carriage-return characters
   - a header that's on line 11 in one file, 16 in another and 23 in a third

   I'm testing whether the model writes defensive code that handles all of this, or code that only works on the 60 lines it saw."

3. **Does it actually know the finance?**
   "In half the tests, I don't give the formula. I just say 'build HML exactly as Ken French does.' The model has to know three things:
   - that the column 'HiBM' (high book-to-market) means cheap stocks
   - that momentum is winners minus losers, while the two reversal factors are losers minus winners
   - that French calculates the size factor, SMB, differently in his 3-factor and 5-factor files

   Flip a sign and you're off by 7 to 9.5 percentage points a month. Swap the two SMB recipes and you're off by 0.6."

4. **Is it consistent?**
   "I run every test 5 times. Right 5 out of 5 is very different from right 3 out of 5. In real work, you can't rerun it and hope."

## How I grade it
"For each run, I measure the typical monthly miss against the official series. That's the root-mean-square error.
- **Pass:** the script ran, it covers at least 95% of the official months, and the typical miss is at most 0.01 percentage points (one basis point). That's basically exact.
- **Why that line:** when I calculated all 8 factors myself, my miss was at most 0.004 percentage points, which is rounding. Every wrong method I tested misses by at least 0.6 points, so there's a wide gap between right and wrong.
- **Labels:** when a model fails, my grader labels why: wrong table, flipped sign, off by 100× (units), dates shifted a month, missing months, crashed, or wrong formula."

## The setup
- **4 Claude models:** Haiku 5.5, Sonnet 5.5, Opus 5.5 and Fable 5.1, from smallest to most powerful.
- **8 factors:**
  - value (HML)
  - size, in two versions (3-factor SMB and 5-factor SMB)
  - profitability (RMW)
  - investment (CMA)
  - momentum (MOM)
  - short-term reversal and long-term reversal
- **11 data files:** 6 files of portfolio returns the models build from, and 5 official factor files that serve as the answer key.
- **2 versions of the instructions:** the exact formula (RECIPE), or just the factor's name (NAME_ONLY).
- **5 repeats** of each combination: 4 × 8 × 2 × 5 = **320 runs**, all graded automatically.
- **Cost:** roughly $20 to $70 in API fees.

"Comparing the two instruction versions is the key part. With the formula given, a failure is a **reading** mistake. Without it, a failure can also be a **knowledge** mistake. So I can tell what each model is missing, not just whether it failed."

## What I've done so far
1. "I tried an easier version first, called Replication Swarm. Haiku, Sonnet and Opus got pre-cleaned files where the job was basically subtracting two columns. All three scored the same correlation, 0.945, so the test couldn't tell them apart. Haiku even got the right number while explaining the method wrong. That's why I made the task harder and the grading stricter."
2. "I downloaded the 11 raw files from Ken French's website and calculated all 8 factors myself. Every one matches the official series within 0.004 percentage points, with correlation 1.0000. So the test is fair and solvable."
3. "I measured how wrong each possible mistake is:
   - wrong table: 1.37 points off
   - size recipes swapped: 0.6
   - sign flipped: 7 to 9.5

   Wrong and right answers are far apart, so grading is clear-cut."
4. "I built a program, with help from Claude Code, that sends each model the task, runs its code safely and grades it. I tested it for free with fake answers that had planted mistakes, and it labeled every one correctly."

## What I expect to find
"I expect bigger models to pass more often: Fable, then Opus, then Sonnet, then Haiku. I also expect the formula to help the small models most. With the formula given, the only hard part left is reading the file, and I expect most of the small models' remaining failures to be wrong-table mistakes."

## Timeline
"Pilot of 8 real runs next week, then the full 320, then about two weeks for the analysis, write-up and talk."

## The takeaway I'm aiming for
"By the end, I'll be able to say something concrete, like: *this model gets it exactly right 95 percent of the time, that one 60 percent, and here's the specific mistake the weaker one keeps making.* That's the evidence you'd want before trusting an AI with real financial data."
