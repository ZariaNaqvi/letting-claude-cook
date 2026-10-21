# Factor Forge: spoken script (about 3 minutes)

My project is called Factor Forge. The question is simple: if you hand an AI model a messy finance data file, can it calculate a well-known number from it *exactly* right? I already know the correct answer, so I can grade it automatically.

Here's why I care. People are starting to use AI for real data analysis, in hedge funds, banks and research. When the AI's code crashes, you notice and fix it. The dangerous case is when it hands you a number that looks completely reasonable but is wrong, and nobody catches it. So I want to measure how often that happens.

Here's a concrete example. In finance there's a standard number called the **value factor**. Every month, it tells you how much cheap stocks beat expensive stocks. Ken French, a finance professor at Dartmouth, sorts all US stocks into six groups (small or big company, and cheap, middle or expensive) and publishes each group's monthly return. To get the value factor, you take four of those columns, average two, average the other two and subtract. That's the whole calculation.

The useful part for me is that French also publishes the official answer, for every month back to 1926. That gives me a 100-year answer key.

So each test works like this. I give the model the first 60 lines of the raw file and ask it to write a Python program that calculates the number. I run its program on the full file and compare the output with the official answer, month by month.

The math is easy. The file is the hard part. It's over 8,000 lines long, with about ten tables stacked on top of each other, and two of those tables have *exactly* the same column names. The model only sees the first 60 lines, so it never sees the second table. It has to guess that it might be there. If its code grabs the wrong one, the answer is off by about 1.4 percentage points every month. No error message, and the numbers look normal.

That's one of four things I'm testing. The second is whether the code can handle the rest of the mess it can't see: yearly rows mixed in with monthly rows, broken lines and invisible characters. The third is whether the model actually knows the finance. In half the tests, I don't give it the formula. I just say "calculate it the way Fama and French do." Then it has to know, for example, that two of these factors run backwards: losers minus winners instead of winners minus losers. Get that wrong and you're off by 7 to 9 points a month. The fourth is consistency. I run every test five times, because right five out of five is very different from right three out of five.

Grading is pass/fail. To pass, the model has to match the official numbers within one hundredth of a percentage point. When I did the calculation myself, I matched within four thousandths, which is just rounding. When a model fails, my grader also labels *why*: wrong table, backwards formula, crashed, and so on.

The full experiment is four Claude models (Haiku, Sonnet, Opus and Fable, from smallest to most powerful), eight different factors, two versions of the instructions and five repeats. That's 320 tests, all graded automatically. The comparison I care most about is between the two instruction versions. If I give the formula and the model still fails, it misread the file. If it only fails without the formula, it didn't know the finance. So I learn *what kind* of mistake each model makes, not just whether it failed.

Here's what I've done so far. I started with an easier version where the models got pre-cleaned files. All three models scored exactly the same, so the test couldn't tell them apart. One even got the right number while explaining the method wrong. That's why I made it harder. Since then, I've downloaded the real data and calculated all eight factors myself. They all match the official answers, so I know the test is fair. I measured how far off each possible mistake is, and right and wrong answers are far apart, so grading is clear-cut. And with Claude Code, I built the program that sends each model the task, runs its code and grades it. I tested it with fake answers that had planted mistakes, and it caught every one.

My prediction is that the bigger models pass more often, and that giving the formula helps the smaller models the most. With the formula given, the only hard part left is reading the file carefully, and I think that's where the small models will slip.

By the end, I want to say something concrete, like "this model gets it exactly right 95 percent of the time, this one 60 percent, and here's the mistake the weaker one keeps making." That's the kind of evidence you'd want before trusting an AI with real financial data.
