---
name: accord-highway-30-49hz-has-no-line
description: RETIRES "at highway 40-49 Hz is wheel order 3" — that p50 of 2.994 was an estimator tautology; there is no spectral line at all in 30-49.5 Hz at highway on any channel or build
metadata:
  type: reference
---

🛑 **SUPERSEDED CLAIM, left visible on purpose:** *"At highway, 40–49 Hz is **WHEEL ORDER 3** —
per-window order p50 **2.994** (n > 600); at 30.8 m/s order 3 = 44.3 Hz, one bin from grind #2 ⇒
anyone peak-finding 40–49 Hz on a highway log will find grind #2 and it will be a tyre."*

**The p50 of 2.994 is an ARITHMETIC TAUTOLOGY, not a measurement.** `order = f0·CIRC/v`, so a
band-limited argmax that sits anywhere near the centre of 30–49.5 Hz, observed at the corpus's median
highway speed of ~28 m/s, returns `40·2.08/28 ≈ 2.97` **whatever the spectrum is doing**. The
statistic cannot distinguish an order from a fixed line from pure noise. Only a **slope** (f0 vs
speed) or a **binned f0 table** tests it, and both refute order 3.

## What replaces it — measured, 2026-08-03
**There is NO spectral line anywhere in 30–49.5 Hz at highway, on any channel, on any build.**
Peak of the **averaged** periodogram (not a per-window argmax), per route × speed bin:

| channel | prominence across 30–49.5 Hz |
|---|---|
| torsion bar `0x18F` | **1.32 – 3.83** |
| comma IMU `ay` | **1.23 – 2.13** |
| comma IMU `gz` | **1.26 – 1.76** |

The kit's own criterion for a real line is **prominence > 4**. Nothing clears it anywhere. Closest
approach: route `3b` at 25–28 m/s, bar peak 37.67 Hz against order 3's predicted 38.22 — **3.83,
sub-threshold**.

**✅ The positive control proves the instrument would see a line.** Peak of the averaged periodogram,
8–30 Hz, pooled routes: 10.94 / 12.61 / 13.66 / 15.40 Hz across speed bins 22–25 / 25–28 / 28–31 /
31–35, against order-1 predictions 11.30 / 12.74 / 14.18 / 15.87 — **prominence 15.2 to 35.6 on the
bar, up to 79 per route.** Free-order fit **1.07**; Theil-Sen slope **+0.4836 [+0.4806, +0.4863]**
vs order 1's 0.4808.

Event `f0` regressed on speed, free 10–49 Hz detector, n = 114: slope **+0.1139 [−0.0539, +0.3072]**
Hz/(m/s) — wheel orders 1/2/3/4 (0.481 / 0.962 / 1.442 / 1.923) are **all excluded**. On/off-order
power ratio over 10–49 Hz: quiet windows **7.24** (matching the kit's 6.94 reference), event peaks
**1.97**. The power is not organised by the wheel-order comb.

## What SURVIVES from the old claim — keep it
- **10–16 Hz at highway IS wheel order 1**, and it is real and strong (prominence up to 79, order
  1.00–1.02 in every speed bin). It remains the correct explanation for the 10–16 Hz band reading
  outside the null in the three-dose table.
- **The general warning stands and is now better founded**: this kit has repeatedly come close to
  publishing a wheel order as a firmware effect. Run the order veto FIRST, and run it as a *slope*
  or a *binned table*, never as a per-window `f0·CIRC/v` median.

⇒ Reproduce with `analysis-2020accord/studies/highway/highway_meanspec.py` (the veto) and
`analysis-2020accord/studies/highway/highway_order_test.py`. See
[[feedback-average-periodograms-before-peak-finding]] for the estimator trap that produced the old
number, [[accord-highway-event-rate-null-with-power]] for what the band *does* contain, and
[[accord-v67-flew-both-grinds-fixed]] for the claim this corrects.
