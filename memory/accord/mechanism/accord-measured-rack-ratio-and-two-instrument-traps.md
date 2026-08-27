---
name: accord-measured-rack-ratio-and-two-instrument-traps
description: The car's variable steering ratio MEASURED from 47 routes — 16.9:1 at centre to 11.1:1 at lock, symmetric, and the firmware's 0xC6B64 compensation is ADEQUATE over 0-120 deg. Kills the "angle-dependent plant-model error" hypothesis. Carries two instrument traps that invalidate other analyses.
metadata:
  type: reference
---

# The rack IS variable-ratio, the firmware DOES know, and it is right where he drives

**Measured 2026-08-13 from 47 routes / 512,895 rows @ 20 Hz / 427.4 min.** Four independent estimators.
[EVIDENCE — `rlog-tools/studies/steering-ratio/measure_steering_ratio.py`, `studies/steering-ratio/ratio_two_sided.py`; cache
`analysis-2020accord/_scratch/cache/ratio/`; trace `docs/traces/TRACE-2026-08-13-measured-steering-ratio.md`.]

```
local steering ratio (wheel deg per road-wheel deg), folded on |theta - theta0|
  1.9 deg  15.65      37.9 deg 16.15      145 deg 13.71
  3.9      16.86      48.0     15.93      191    13.50
  6.3      16.65      60.2     15.02      236    12.81
  9.4      15.60      75.7     14.52      303    11.67
 12.9      15.72      94.5     13.97      380    11.06
 17.4      16.20     120.7     13.75
```
**swing 0->120 deg = 1.176 [1.147, 1.201]** · plateau 13.73:1 · **centre offset theta0 = -4.25 deg**
(openpilot's learned `angleOffsetAverageDeg` = -4.78; sensor zero sits LEFT of true centre).

## The firmware's compensation is ADEQUATE, and the desk estimate was wrong
`FUN_0003b8f6` (the 1 kHz plant model) **reads absolute steering angle** — `0x3ba12 ld.hu -0x6a10,gp,r15`
— and indexes `0xC6B64` (`movea 0x7b64,tp,r10` @`0x3ba1c`), **virgin across all 96 images**:
```
X (0.1 deg/ct):     0   340   640   850  1000  1200 ... 4776
Y (Q10, 1024=1.0) 899   908   981  1060  1083  1084 ... 1084      swing 1084/899 = 1.206x
```
🛑 **1.176 measured vs 1.206 modelled — the firmware is ~2.5 % OVER, not 40 % under.** Agreement is
**0.01-0.07 at every one of its own knots** over 0-120 deg.
🛑 **The 1.67-1.82x figure read off the service-manual schematic is REFUTED** — that graph is schematic
("High"/"Low", no axis values) and its notch DEPTH is not recoverable from it. **Do not re-derive a rack
number from that image.**
⊕ **What IS uncompensated:** beyond 120 deg the rack keeps quickening (0.805 of plateau at 380 deg) while
the table is flat ⇒ ~20 % uncompensated — but **ALL exposure beyond 120 deg occurs below 5 m/s**, so it is
a parking-manoeuvre effect. **65 % of engaged time is inside 0-34 deg, where compensation is correct.**
⇒ 🛑 **The "angle-dependent plant-model error explains the grinding" hypothesis is DEAD in the band he
drives.** So is "the plant model is structurally blind to rack position" — it is not blind.

## The rack is SYMMETRIC, and that is a detection claim, not an absence of evidence
Paired block bootstrap, LEFT vs RIGHT: **all 19 per-bin CIs cover equality**, as do plateau and lock.
⭐ **An INJECTED 2 % asymmetry is caught on every statistic (geo, outer, ref120, lock all exclude 1 at
f=0.98) ⇒ a real >=2 % asymmetry is EXCLUDED.** An earlier "left is 3-5 % quicker" was a 2-3 bin median
plus unequal exposure — **retracted.**
**theta0 is exonerated both ways:** sweeping -7.00 -> -1.50 deg moves the L/R difference by only **0.9 %**,
less than its own CI half-width, and no plausible centre makes the sides coincide. The per-side theta0
refits disagree (-3.98 vs -4.43) but that is **chord extrapolation** — widen the window and the split grows
monotonically while the **midpoint stays pinned at -4.21 deg**, on the joint fit.
⚠ A residual 1.5 % beyond 105 deg survives one statistic but **dies in every narrow speed band, and is
absent from both IMU-free estimators while present in both IMU-based ones** ⇒ instrument, not rack.
⚠ **Per-side toe / tyre radius is UNRESOLVABLE from this data** — never attribute a vehicle asymmetry to
the rack.

## 🛑🛑 TWO INSTRUMENT TRAPS — both invalidate existing analyses
1. **`carState.yawRate` is IDENTICALLY ZERO on this car** — **0 nonzero of 512,895 samples.** Anything in
   the kit reading `cs_yaw` is reading zeros. Use **`livePose.angularVelocityDevice.z`**; the device frame
   is **z-DOWN**, so it is **NEGATIVE on a LEFT turn**.
2. **`vEgo` is NOT a valid speed reference for any rear-axle kinematic quantity at non-trivial steering
   angle.** It averages all four wheels; the fronts run at `v/cos(delta)`, so `vEgo/v_rear` goes
   0.989 at centre -> **1.079 at 250-400 deg**. 🛑 **That bias is shaped exactly like a flat plateau: it
   produced a FALSE PASS of this study's own positive control and would have given the wrong answer.**
   Use **`(ws_rl + ws_rr)/2`** — undriven, unsteered, a rigid-body identity.

## Method notes worth reusing
- Four estimators with **disjoint dependencies**: yaw+rear `1.242`, yaw+front `1.211`, rear differential
  (**no IMU**) `1.160`, **wheel speeds only** (no IMU, no yaw, no wheelbase, no track) `1.226`.
- **Synthetic-rack nulls** beat a shuffle control here: a genuinely flat rack reads back **0.979
  [0.968, 0.988]** through the identical pipeline, so the pipeline cannot manufacture the droop. A shuffle
  is **uninformative by construction** on this statistic — it kills the sign relation and returns
  [-1.43, +1.49]. **Retire the shuffle; use injection.**
- Fitted understeer gradient **K = 0.00225 s^2/m** (fitted, not assumed); wheelbase L = 2.83 m.
- **Lock-to-lock is MEASURED, not assumed: ~+-390-400 deg** (p99.9 == max on three routes ⇒ a hard stop).
- Bootstrap over **BLOCKS** (312 in the primary band), never windows.

Related: [[accord-c6200-clamps-the-pid-reference]] · [[accord-steering-sign-convention-confirmed]] ·
[[feedback-run-the-control-before-the-measurement]] · [[feedback-exposure-law-contiguous-blocks-not-total-seconds]] ·
[[accord-4x-lkas-gain-is-the-frozen-variable]] · [[reference-accord-two-memory-stores-have-diverged]]
