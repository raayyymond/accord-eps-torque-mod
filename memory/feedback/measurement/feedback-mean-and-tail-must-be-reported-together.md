---
name: feedback-mean-and-tail-must-be-reported-together
description: 🛑 A matched-cell mean and an extreme-tail census answered the SAME question with OPPOSITE signs in one session (0.913 [0.791,1.026] vs 27/219 blocks against 1/91). Each alone is a confident wrong answer. Report both, name the population each describes, and check the tail thresholds actually reach the phenomenon.
metadata:
  type: feedback
---

# 🛑 Report the mean AND the tail, and say which population each describes

**2026-08-01.** Testing whether V62/V65's rate-lane doubling raised the 30–49 Hz band, two analyses of
the *same data* disagreed in sign:

| method | result | reads as |
|---|---|---|
| matched-cell, episode-bootstrapped **mean** | 30–49 Hz **0.913 [0.791, 1.026]**, inside the split-half null floor | a confident **NULL** |
| extreme-tail **burst census** | **27/219 blocks** at Kd=2× vs **1/91** at Kd≤1×; max **325 → 4046** | a confident **POSITIVE** |

**Both were misleading on their own, for opposite reasons.**

**Why:** the matched-cell exceedance thresholds **never reached the phenomenon**. The matched q99
threshold was **317**; the bursts are **3000–4000**. The matched analysis was describing the bulk and
was structurally blind to the events in question. Meanwhile the census was uncontrolled for exposure,
and two of its three high-dose routes were **driven specifically to provoke the symptom** — so its
burst *rate* was not comparable at all.

## What to do

1. **Whenever the symptom is bursty, report the mean and the tail side by side**, and state in one line
   which population each describes. The kit already says *"mean Welch power is the wrong statistic for
   a bursty limit cycle"*; the new half is that **a tight null CI on a mean is evidence about the mean
   only** and must not be quoted as a null on the phenomenon.
2. **Print the tail thresholds next to the event amplitudes.** If q99 of your matched set is an order
   of magnitude below the events you are testing for, your test cannot see them. This check is free and
   would have caught it immediately.
3. **Ask what the route was FOR.** A route driven to demonstrate a symptom cannot be evidence that the
   symptom's rate rose. Mark provoked routes and quote the ordinary-driving route separately.
4. **Condition on the corner the phenomenon lives in**, and report each arm's **exposure in seconds**
   there. If the comparison arm never visited that corner, the contrast is undefined — say so rather
   than reporting a ratio.

⚠ This is a *third* distinct way this kit has manufactured a wrong effect size from correct arithmetic,
after window-vs-episode bootstrapping and the Simpson's-paradox `f0` shift. All three share a root:
**a statistic was computed correctly over the wrong population.**

See also [[feedback-episodes-not-windows]], [[accord-v62-fixed-the-grinding]].
