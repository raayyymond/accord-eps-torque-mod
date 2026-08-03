---
name: feedback-check-the-data-exists-before-concluding-it-doesnt
description: Two sessions asserted "no Kd=1 highway baseline exists" without checking; route 2b had 227 s of it, and finding it refuted a confident prediction
metadata:
  type: feedback
---

🛑 **On 2026-08-02 a confident, arithmetically-correct prediction was refuted by data that had been
sitting in the repo for weeks — and the only reason it was found is that someone ran the exposure count
instead of repeating the assertion.**

**The prediction:** V67 replaces a speed-scheduled gain surface with a flat scalar, so it delivers
**2.44×** at highway (its maximum, 22% above V62's 2.00× — the dose that raised 40–49 Hz by 11.7×).
The operator reported a highway resonance. Tidy, mechanistic, and it matched the symptom.

**The check that killed it:** counting highway-engaged seconds per cached route. Route **`2b` (V58,
Kd = 1.00×) has 227 s of highway** — the baseline everyone had assumed did not exist. With it, the
three-dose highway comparison is **null** (ratios 0.98 and 0.77 against a split-half null of
[0.53, 1.86], zero burst windows at any dose across ~1,400 s).

**Why:** the belief "there is no Kd = 1 highway exposure" was formed when the grind #2 work was
creep-only, was true *of the routes then in play*, and was then **repeated across two sessions as a
property of the corpus**. Nobody re-derived it after new routes were added.

## How to apply
- **Before concluding a measurement cannot be made, count the exposure across the whole corpus.** It is
  one cheap loop over the caches and it takes seconds. `analysis-2020accord/r47_orchestrator_checks.py
  exposure` does exactly this — run it whenever a comparison looks under-powered.
- **A scoping claim inherited from a previous session is not evidence.** Treat "we don't have data for
  X" the same way as any other load-bearing claim: re-derive it, or label it as unverified.
- **This is the same failure as V57's probe.** `gp-0x6806`'s polarity sat measured in
  `_cache_r28`/`_cache_r29` for a month while every session treated it as an open Ghidra question. The
  general rule is now recorded twice: **check whether the answer is already on disk before spending
  effort — tracing, or asserting it cannot be had.**
- **When your own arithmetic makes a tidy story with the operator's report, that is when to look
  hardest for the disconfirming dataset**, not least hard. This kit's recorded failure mode is *a
  statistic computed correctly over the wrong population*; three prior instances are on record, and
  this would have been the fourth.

Related: [[accord-gp6806-is-the-lkas-gate-validated-on-car]],
[[feedback-mean-and-tail-must-be-reported-together]], [[feedback-episodes-not-windows]],
[[accord-v67-flew-both-grinds-fixed]].
