---
name: accord-grind1-is-a-movable-pole-and-alpha2-is-its-handle
description: "On the corrected 21-26 Hz band, grind #1's PEAK FREQUENCY tracks alpha2 (0xC40DC): alpha2=22 gives about 23.5 Hz and alpha2=14 about 21.1 Hz, ratio 1.113 with CI [1.06, 1.17] and p 0.035. A frequency that moves with a calibration is a CLOSED-LOOP POLE and is relocatable in firmware - the opposite of the 7.8 Hz oscillation, whose f0 was invariant to a 2x forward-gain change. alpha2 also hits on amplitude, 1.340 with CI [1.12, 2.29]. V109 already moved alpha2 22 to 14, which was the right direction on both endpoints, and V115 (alpha2 14 to 8) is already built and unflown. The confound is that alpha2=14 exists only on V111/V112, so it is collinear with build era."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑 GRIND #1 IS A **MOVABLE POLE**, AND `alpha2` IS ITS HANDLE

## ✅ THE STRUCTURAL FINDING: THE FREQUENCY MOVES
The kit classified the ~23 Hz line as a pole once before because it **moved 20.3 → 23.0 Hz**, and
classified the 7.8 Hz oscillation as **mechanical** because its `f0` was **invariant to a 2×
forward-gain change** ([[accord-the-78hz-mode-does-not-move-with-firmware-gain]]). Applying the same
test to grind #1 on the **corrected 21-26 Hz band**, 13 Lever-B-ON routes:
```
   B) FREQUENCY (peak location, 15-40 Hz, top-quartile windows)
      a2_C40DC (14 vs 22)   rho +0.587  p 0.035   hi/lo 1.113   CI [1.06, 1.17]  <== HIT

   A) AMPLITUDE (21-26 Hz share of 1-45 Hz, p90)
      a2_C40DC (14 vs 22)   rho +0.537  p 0.059   hi/lo 1.340   CI [1.12, 2.29]  <== HIT
      knee_C40BC            rho -0.406  p 0.168   0.622  [0.29, 1.52]
```
✅ **`alpha2 = 22` → about 23.5 Hz; `alpha2 = 14` → about 21.1 Hz.** Both CIs exclude 1.0.
⇒ **grind #1 is a CLOSED-LOOP POLE — relocatable in firmware, not merely dampable.** That is a
categorically better position than the 7.8 Hz oscillation, where *move it* was refuted, *damp it* was
measured-closed, and only *excite it less* remained.

## ✅ `alpha2` MOVES BOTH ENDPOINTS THE SAME WAY, AND V109 ALREADY WENT THE RIGHT WAY
`alpha2 = 14` is **lower frequency AND 34 % less band content** than `alpha2 = 22`. **V109 changed it
22 → 14** (`_v109_V109-V108BASE-ALPHA2.C40DC.14`), so that step was correct on both endpoints —
**which the kit did not know at the time**, because every grind measurement was on the wrong band.
✅ **`V115` (`alpha2` 14 → 8, V112 base) IS ALREADY BUILT AND UNFLOWN** — image `5f804a8a…`, rwd
`f1a47bb7…`, 42/42 assertions. **It is the direct next step on this axis and needs no new build.**

## 🛑 THE CONFOUND, STATED PLAINLY
`alpha2 = 14` exists **only on V111 and V112** (3 routes), so it is **collinear with build era** — any
late-build effect appears as an `alpha2` effect. ⊕ Partial separation exists because `knee` varies
**within** the `alpha2 = 22` group (300 and 600) and V111/V112 differ in `knee` (600 vs 1800), but
**this is not clean.** ⇒ **[EVIDENCE that the frequency is firmware-movable; BELIEF that `alpha2`
specifically is the mover.]**
⚠ `K1_C40D2` also hits on both (amplitude 0.794 [0.51,0.97]; frequency 0.916 [0.86,0.96]) but is
**perfectly confounded with `knee`** ([[accord-k1-and-knee-are-perfectly-confounded]]).
⚠ The friction-row cells show `rho = +0.729, p = 0.005` on amplitude but their arms are **5 vs 1** —
**do not read that as a result.**

## ⇒ WHAT THIS CHANGES
1. **Grind #1 has a better prognosis than the peak-turn oscillation.** Its pole moves; the
   oscillation's does not.
2. **V115 becomes a serious candidate** — already built, already on the right axis, and now with a
   measured dose-response behind it on the corrected band.
3. 🛑 **`alpha2`'s direction must be checked against its OTHER role** before flying: it sets the
   `gp-0x6b26` bandpass upper corner, and lowering it *rotates* that vector (damping up, mass down).
   **That interaction is not analysed here.**
Tool: `rlog-tools/studies/peakturn/grind_lever_hunt_corrected_band.py`.
