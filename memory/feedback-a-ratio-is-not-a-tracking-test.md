# 🛑🛑 A RATIO OF TWO LINES IS NOT A HARMONIC TEST — shuffle the pairing

**Recorded 2026-08-05 after the orchestrator published, retracted, and re-confirmed the same claim inside
one session.** This is a method rule, not a firmware fact.

## What happened
An agent measured **f_hi/f_lo = 2.003 [1.997, 2.008]** over 156 windows and concluded that grind #2
(~43 Hz) **is** grind #1's (~21 Hz) 2nd harmonic. It looked airtight — free peak-finding geometry
permitting 1.35–3.27 so "2.000 could not be manufactured", a passing negative control, and a
residual-fit test against a rival fundamental. **The orchestrator promoted it to the session headline,
put it in the design doc, the handoff, a memory file, the commit message, and the report to the operator.**
**It was wrong.**

## Why it was wrong
**If f_lo ~ N(21, 1.2) and f_hi ~ N(43, 2.6), then `median(f_hi/f_lo) ≈ 2` WHETHER OR NOT THEY EVER MOVE
TOGETHER.** The ratio is a property of the two **marginal** distributions. Orchestrator-verified by
simulation: two **independent** lines with those marginals return **median ratio 2.048, CI [2.012, 2.072]**
— indistinguishable from the "finding".
**Harmonicity requires f_hi to TRACK f_lo window-to-window: a SLOPE of 2.0, not a RATIO of 2.0.**

## ★ THE TEST THAT SETTLES IT — shuffle the pairing
If a paired statistic encodes real pairing, **destroying the pairing must destroy the statistic.**

| route | observed ratio | **shuffled ratio** | **tracking slope** |
|---|---|---|---|
| `r54` | 2.238 | **2.227 [2.215, 2.238]** | **0.106 [−0.056, +0.264]** |
| `r58` | 2.288 | **2.268 [2.252, 2.284]** | **0.097 [−0.120, +0.337]** |

The shuffled ratio **reproduces** the observed one ⇒ no pairing information. Every slope contains 0 and
excludes 2.0, on four routes. ⇒ **the corpus's original "slope 0.173 [−0.92, +1.59], NOT a harmonic" is
CONFIRMED, not reversed.**

## The rules this leaves
1. **For any claim of the form "B is a multiple/function of A", regress B on A and report the SLOPE.**
   A ratio, a median ratio, or a CI on a ratio is not that test.
2. **Run a shuffle/permutation control on every paired statistic.** If the statistic survives shuffling,
   it was never about the pairing. This is cheap and it is decisive.
3. **An implausibly tight CI is a red flag on its face.** ±0.005 on a ratio of two lines with ~6%
   relative spread should have prompted a check before publication, not after.
4. ⚠ **"Free geometry means 2.000 cannot be manufactured" is a non-argument.** The geometry does not need
   to manufacture it — the marginals already do.

Related: [[feedback-episodes-not-windows]] (the same family: a statistic that looks significant because
the wrong thing was treated as the unit) · [[accord-a-caveat-can-mutate-into-a-result]]
