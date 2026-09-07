---
name: accord-grind1-cal-only-levers-on-v282-are-exhausted-the-lag-pole-is-a-waterbed-and-the-d-clamp-trades-the-ring
description: 2026-09-06 session (docs/research/GRIND1-LOOP-SHAPE-V287-2026-09-06.md + Appendices A-C, docs/review/ADV-V287-*.md, docs/traces/TRACE-2026-09-06-lag-and-fb-pole-census-v282.md). Every cal-only lever for grind #1 (the 18-22 Hz rate-loop crossover resonance) on the V282 base was priced on one model anchored to the measured loop; none removes it without a trade. Output-lag pole 0xC63EC/EE is a WATERBED (the sensitivity peak already sits at ~26 Hz; every raise cuts 18-22 and grows 26-33; 15 Hz takes GM below 1, DO-NOT-FLASH); fb pole 0xC63E8/EA is a gain lever with no phase effect (rectified, multiplicative); Kd closed; Kp cut costs 35 % of tracking the outer loop cannot repay; 0xC6446->2048 is a large free lever for the 7.3 Hz ring but halves 20 Hz damping; the D clamp 0xC61B6 (NOT 0xC61BA, which is the integrator anti-windup) is an excitation limiter hands-off at every speed but in loaded/hands-on/fast-wheel strata (20-28 % of engaged time) becomes a 0.6x Kd cut that re-arms the ring -- 2560 FAILED the adversarial pass; 7680 is the largest ring-safe dose and is a ~5 % partial mitigant needing ~38 min of ordinary engaged driving to resolve. There is NO cal on the setpoint path from the 0xE4 byte to E = 32*sp - fb (all clamps, no state); the 100 Hz command staircase reaches D unfiltered, so softening the kick without touching feedback D needs a CODE edit (setpoint interpolation across the 10 PID ticks) -- the identified real target, not built.
metadata:
  type: reference
---

# Grind #1 cal-only levers on V282 are exhausted -- 2026-09-06

**EVIDENCE (model anchored on the measured loop; base row reproduces creep20's Ms 2-2.9 and the GM 1.77x):**

| lever | Re@7 | S@20 | GM | ring L_tot | verdict |
|---|---|---|---|---|---|
| as-built V282 | -0.23 | 1.61 | 1.77x | 0.980 | -- |
| lag pole 8 Hz 974/792 | +0.69 | 1.21 | 1.19x | 0.822 | waterbed: 26-33 Hz motion x2.28 (delay plant) -- a plant DISCRIMINATOR only |
| lag pole 15 Hz 932/1458 | +1.84 | 0.63 | **0.72x** | -- | **DO NOT FLASH** |
| 0xC6446 -> 2048 | +0.62 | 1.61 | 1.77x | **0.479** | stutter build, not a grind build (20 Hz damping 1.52 -> 0.68) |
| Kd 64..96 | -- | 1.67-1.71 | up | -- | moves the sensitivity peak INTO 20 Hz |
| Kp 160 | -- | 1.38 | 1.91x | 0.912 | costs 35 % inner DC tracking; SteerKP headroom only 1.125x |
| D clamp 2560 | -- | as-built hands-off | -- | **1.038 loaded** | FAILED adversary B (Kd_eff 95 at ang>60) |
| D clamp 7680 | -- | as-built | -- | 0.983 (= gate) | partial mitigant, onset x0.93-0.95, needs n~1150 onsets |

**Why:** GRINDING-DEEP-ANALYSIS ranked the 15 Hz lag pole first without ever running the Nyquist crossing; Appendix B's D-clamp admissibility was computed only on creep and bookmarked-episode windows. Adversary B's stratification (hands-on bar>700, loaded ang>60, fast wheel >25 deg/s) is now the required test for any nonlinear lever.

**How to apply:** do not re-propose these cells as grind levers. The next class is a setpoint-side code edit (interpolate the 100 Hz staircase over the 10 PID ticks: cuts the D kick ~10x, zero DC cost, zero feedback-D cost) with GATE 1 (a new RAM state cell) and the cave discipline. Related: [[accord-honda-oscillation-detector-is-live-and-cuts-motor-demand-x06-through-governor-slot-2]], [[accord-the-d-clamp-is-0xc61b6-and-the-102-deadband-is-gated-off-engaged]], [[accord-r24-pumps-at-7hz-and-damps-at-20hz-the-same-cell-pulls-the-two-symptoms-opposite-ways]], [[accord-the-r24-arm-magnitude-decides-the-sign-of-the-kd-axis]].
