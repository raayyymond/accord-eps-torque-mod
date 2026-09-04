---
name: accord-the-lkas-command-band-is-0-to-075hz-so-inner-loop-fidelity-is-a-dc-statement
description: 2026-09-04, MEASURED by subagent zn39 over 5 routes (Welch on the engaged LKAS command). 95% of engaged lateral-command energy lies below 0.59-0.74 Hz and 97.5-98.3% below 1 Hz. EVERY dynamic feature of the EPS rate loop sits 7x-27x ABOVE that band - the 5.05 Hz output-lag pole, the 7.3 Hz strong-turn ring, the 9.64 Hz P/D corner, the 16.5 Hz feedback EMA, the ~20 Hz creep grind. Consequences, all binding on future sizing: (1) if the inner loop is specified as an ACTUATOR that "merely delivers the demanded angular acceleration" (operator, 2026-09-04), the flat-response criterion COLLAPSES to a pure DC statement |T(0)| = 1.0 - today it is 0.535, a 1.87x scale error; (2) INNER-LOOP PHASE LAG CANNOT DISCRIMINATE CANDIDATES - it spans 1.32 deg (4.9 ms) across every (Kp,Kd) pair considered, against the operator's own 200 ms SteerDelay, so any argument of the form "this adds lead and therefore helps" is measuring a 0.7% effect; (3) what remains as real criteria are PEAKING (max|T|) and LINEARITY (the demand-dependent deadband). Nothing the operator ASKS for is anywhere near the frequencies where this loop misbehaves - so every symptom he feels is the actuator's own dynamics, not tracking error.
metadata:
  type: reference
---

# The LKAS command band is 0-0.75 Hz - so "fidelity" is a DC statement, and lag arguments are dead - 2026-09-04

Measured by subagent `zn39`, Welch PSD of the engaged LKAS lateral command across **5 routes**.
Source: `docs/research/ZN-BACKWARDS-NO-OVERSHOOT-2026-09-04.md` Part II.

## The measurement

| quantity | value |
|---|---|
| 95 % of engaged command energy below | **0.59-0.74 Hz** |
| 97.5-98.3 % below | **1 Hz** |

Every dynamic feature of the EPS rate loop sits **7x to 27x above** that band:

```
  command band  |  0.75 Hz
  lag pole      |  5.05 Hz   (6.7x)
  7.3 Hz ring   |  7.3  Hz   (9.7x)
  P/D corner    |  9.64 Hz   (12.9x)
  feedback EMA  | 16.53 Hz   (22x)
  creep grind   | ~20.3 Hz   (27x)
```

## Why it matters - it retires a whole class of argument

The operator's spec, 2026-09-04: *"Innerloop is merely responsible for accelerating the steering
angle as demanded by outerloop."* That makes the inner loop an **actuator**, judged on fidelity. But
because the command band is 0-0.75 Hz:

1. ⭐ **"Flat magnitude across the command band" COLLAPSES TO `|T(0)| = 1.0`.** It is a pure DC
   statement on this car. **Today `|T(0)| = 0.535`** - a **1.87x scale error** the outer loop's
   integrator absorbs. A Kp cut to 148 would make it 0.407 (2.46x), i.e. **worse** on fidelity.
2. 🛑 **INNER-LOOP PHASE LAG CANNOT DISCRIMINATE.** Across every candidate pair the lag at the top of
   the command band spans **1.32 deg = 4.9 ms**, against the operator's own **200 ms** `SteerDelay`.
   The whole Kd 128->160 move is **1.4 ms, ~0.7 %** of it. ⇒ **Any argument of the form "raising Kd
   adds lead and therefore reduces outer-loop overshoot" is real in DIRECTION and negligible in
   SIZE.** (The orchestrator advanced exactly that hypothesis; it was correct and worthless.)
3. **What survives as real criteria: PEAKING (`max|T|`) and LINEARITY (the demand-dependent
   deadband).** Those two carry the entire inner-loop decision.

## The corollary worth remembering

**Nothing the outer loop ASKS for is anywhere near the frequencies where this loop misbehaves.**
⇒ every symptom the operator feels - grinding, ringing, stutter - is the actuator's **own dynamics**,
not a tracking error. Fixing them is a question of what the actuator does when *undisturbed*, not of
how well it follows.

Related: [[accord-the-rate-pid-in-the-acceleration-frame-is-a-PI-our-P-is-its-integral-and-our-D-is-its-proportional]],
[[accord-the-r24-arm-magnitude-decides-the-sign-of-the-kd-axis]],
[[accord-the-creep-grind-is-the-lkas-rate-loop-crossover-resonance-d-dominated]].
