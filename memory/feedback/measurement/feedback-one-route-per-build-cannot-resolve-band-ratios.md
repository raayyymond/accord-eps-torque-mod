---
name: feedback-one-route-per-build-cannot-resolve-band-ratios
description: "Two drives on IDENTICAL firmware (r22, r23, both V112) differ by 2.74x [0.79, 8.87] in 6-9 Hz p90 at 20-60 deg of steering angle. So any cross-build band-ratio comparison built on one route per arm cannot resolve effects below that, and window-level bootstrapping understates the true uncertainty because it ignores route-level variance. This invalidated both a mechanism refutation and the residue it left behind, within one session."
metadata:
  node_type: memory
  type: feedback
---

# 🛑🛑 ONE ROUTE PER BUILD **CANNOT** RESOLVE A BAND RATIO — measured, 2026-08-28

## THE MEASUREMENT
`r22` and `r23` are **both V112** — identical firmware, different drives. 6–9 Hz rate rms, p90, by
steering-angle band:
```
   |ang|     SAME-FIRMWARE r23/r22    95% CI          cross-build V112/V111
    0-  5           1.07x           [0.81, 1.25]            1.27x
    5- 20           0.77x           [0.55, 0.97]            0.90x
   20- 60           2.74x           [0.79, 8.87]            0.75x
```
🛑 **At 20–60° two drives on the SAME firmware differ by 2.74×**, and the cross-build ratio sits well
inside that spread. **Drive-to-drive variation is as large as, or larger than, every cross-build
difference measured.**

## 🛑 WHAT IT COST, IN ONE SESSION
1. A **mechanism refutation** — "V112's friction term is 1.9–3.0× V111's at high rate, yet V112 is
   not worse, therefore the K1 mechanism is refuted." **Withdrawn.** The comparison cannot resolve a
   2–3× effect when same-firmware drives differ 2.74×. **The mechanism is UNTESTED, not refuted.**
2. The **"residue"** that refutation left behind — "V112 is 1.27× worse at 0–5° where the friction
   term is identical, so something else differs." **Withdrawn.** Same-firmware gives 1.07×
   [0.81, 1.25]; 1.27× is marginal against that and needs no new mechanism.

## ⭐ THE METHODOLOGICAL RULE
**Bootstrapping WINDOWS understates the uncertainty of a cross-build claim**, because windows within
a drive are not independent samples of "what this firmware does" — the drive itself is the unit.
✅ **Resample ROUTES, or report the same-firmware spread alongside every cross-build ratio.**
✅ **A cross-build band ratio needs ≥ 2 routes per arm** before it means anything, and at large
steering angle it needs an effect **> ~2.7×** to clear the drive-to-drive floor.
⊕ This is the same lesson as [[feedback-episodes-not-windows]] one level up: that note says bootstrap
over episodes rather than windows; this one says **bootstrap over DRIVES** when the claim is about a
build.

## ⚠ WHAT THIS DOES *NOT* INVALIDATE — and why
[[accord-the-oscillation-excess-is-ANGLE-GATED]] compares **stock vs V112** and survives, but only
because its effect is **larger than the floor**: stock's entire distribution tops out at **3.748**
while V112 reaches **16.568** (**4.4×**), and at 20–60° stock's max is **2.111** against V112's
**16.568** (**7.9×**) — both above the 2.74× same-firmware spread. ⊕ It is also **exposure-controlled
with the confound inverted** (stock drove the regime *more*).
🛑 **But it rests on ONE stock route (97).** Treat it as strong-but-single-arm, and do not read the
smaller per-band ratios (1.06–1.74×) as resolved — **only the 4–8× tail differences clear the floor.**
