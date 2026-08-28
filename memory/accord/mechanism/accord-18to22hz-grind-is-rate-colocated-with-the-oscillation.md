---
name: accord-18to22hz-grind-is-rate-colocated-with-the-oscillation
description: "The 18-22 Hz grinding and the 7-9 Hz oscillation occupy the SAME motor-rate regime (59.3 vs 59.5 percent of band energy above 40 deg/s), so NO rate-scheduled lever can separate them. The 26-31 Hz band is different: only 2.6 percent of its energy is above 60 deg/s, so a scheduled cut spares it with 10-17x selectivity. This makes the Kd refusal sharper rather than lifting it, and it corrects an earlier framing that reported rate AUC 0.630 without saying the comparison was against hard curves specifically - against ordinary driving rate separates at AUC 0.978."
metadata:
  node_type: memory
  type: reference
---

# ⭐⭐ THE 18-22 Hz GRIND IS **RATE-COLOCATED** WITH THE 7-9 Hz OSCILLATION

## 🛑 FIRST, A CORRECTION TO MY OWN FRAMING
I reported *"the rate axis gives AUC 0.630 ⇒ weak separation, lever parked."* **The number is right;
the framing was incomplete.** 0.630 was measured against **normal HARD CURVES** (n = 106). Against
**ordinary driving** (n = 4,920) the same axis gives:
```
   axis                     AUC     median osc   median normal   ratio
   RATE  p95|rate|         0.978      47.06         4.33        10.86x
   ANGLE p95|ang|          0.713       9.05         4.50         2.01x
```
✅ **Rate separates the oscillation from ordinary driving almost perfectly**, and beats angle doing
it. What it cannot do is separate the oscillation from a **hard curve** — and the operator's own
description says why: *"a fixed oscillation during the peak of a hard curve."* **The symptom IS the
hard-curve regime.** ⇒ "spare hard curves" and "fix the oscillation" are in direct tension **by the
structure of the problem, not by a measurement failure.** What a scheduled lever CAN spare is
ordinary driving.

## [EVIDENCE] THE BAND TEST — 8,200 engaged windows, 17 routes
Share of each band's **power** sitting above a knot at T deg/s (= the share a rate-scheduled cut
would act on):
```
   band                     T=20     T=40     T=60    T=100    T=140
   6-9 Hz   (oscillation)   82.7 %   59.3 %   26.2 %   15.8 %   12.2 %
   18-22 Hz (grind)         94.1 %   59.5 %   23.9 %   14.6 %   11.0 %
   26-31 Hz (grind)         92.7 %   64.4 %    2.6 %    1.1 %    0.7 %

   selectivity = 6-9 share / grind share      vs 18-22    vs 26-31
                                    T=60         1.10x      10.15x
                                    T=140        1.11x      16.68x
```
`STATE-ARCHIVE-2026-08-11` measured **D PUMPS 2-12 Hz and DAMPS 16-35 Hz**, so a flat `Kd` cut buys
**+0.077** at 6-9 and costs **-0.217** at 18-22 and **-0.336** at 26-31. Beating that needs
selectivity **> 2.82×** and **> 4.36×** respectively.
✅ **The 26-31 Hz cost is SOLVED** by scheduling: 10-17×, far past the 4.36× needed — only 2.6 % of
that band lives above 60 deg/s.
🛑 **The 18-22 Hz cost is NOT**: 1.10× against a required 2.82×. **18-22 Hz and 6-9 Hz sit in the
same rate regime** (59.5 % vs 59.3 % above 40 deg/s).

## ⇒ TWO CONSEQUENCES
1. **`Kd` stays REFUSED**, with a sharper reason than before: scheduling fixes the 26-31 Hz half of
   the trade and leaves the 18-22 Hz half roughly intact ⇒ still net negative, ~2.6× against instead
   of 3-4×. **Not a build.**
2. ⭐ **A GENERAL CONSTRAINT ON THE WHOLE SEARCH: no rate-scheduled lever can act on the 7-9 Hz
   oscillation without equally acting on the 18-22 Hz grind.** Any such lever helps one and hurts the
   other **in the same windows**, because `D` pumps at 6-9 and damps at 18-22. ⊕ It also raises the
   question of whether the two are **one mechanism** rather than two — they are rate-colocated to
   within 0.2 percentage points, which is not what two independent phenomena usually look like.
   🛑 That is a hypothesis, not a finding: co-location in rate is **necessary but not sufficient**
   for a shared mechanism, and [[accord-two-symptoms-two-mechanisms-rez-spectrum]] separates them on
   the `Re(Z)` spectrum. **The two records are not yet reconciled.**
Tools: `rlog-tools/studies/peakturn/rate_axis_separation_roc.py` (ROC),
`rlog-tools/studies/peakturn/band_energy_vs_rate_knot.py` (this).
